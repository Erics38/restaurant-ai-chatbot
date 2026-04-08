"""
Restaurant AI — FastAPI application entry point.

This file wires everything together:
  • Configures logging (file + stdout)
  • Creates the FastAPI app with CORS and static file serving
  • Registers startup/shutdown lifecycle hooks
  • Defines all HTTP endpoints

Endpoint overview:
  GET  /                         → Serve the chat UI (restaurant_chat.html)
  GET  /health                   → Health check for Docker / load balancers
  GET  /menu                     → Full menu data (used by the frontend)
  POST /chat                     → Main chat endpoint; persists messages to DB,
                                   calls Tobi AI, returns Tobi's reply
  GET  /chat/history/{session_id}→ Return all messages for a session (used on
                                   page load to restore conversation history)

In development mode (ENVIRONMENT=development) the OpenAPI docs are available at:
  /api/docs  (Swagger UI)
  /api/redoc (ReDoc)
In production these are disabled to avoid leaking API structure.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as ORMSession

from .config import settings
from .models import ChatRequest, ChatResponse, HealthResponse, DBSession, DBMessage
from .tobi_ai import get_ai_response_with_context
from .menu_data import MENU_DATA
from .database import get_db, init_db


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
# Must happen before the FastAPI app is created so that any log calls during
# startup are captured.
# Logs go to both a rotating file (logs/app.log) and stdout (visible in
# `docker compose logs`).
# ---------------------------------------------------------------------------
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file),  # Persistent file log
        logging.StreamHandler(),                  # Docker / terminal output
    ],
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Restaurant AI",
    description="The Common House — AI-powered restaurant ordering system",
    version="1.0.0",
    # OpenAPI docs exposed only in development to keep production lean and secure
    docs_url="/api/docs"  if settings.is_development else None,
    redoc_url="/api/redoc" if settings.is_development else None,
)


# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------
# Allows the browser-based frontend to call this API even if it's served from
# a different origin (e.g. a CDN or a different port during development).
# Controlled via the ALLOWED_ORIGINS environment variable.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],   # Allow GET, POST, OPTIONS, etc.
    allow_headers=["*"],   # Allow Content-Type, Authorization, etc.
)


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------
# Mounts the static/ directory so that /static/... URLs serve files directly.
# The chat UI (restaurant_chat.html) is served via the GET / endpoint below,
# not from /static, so users just visit the root URL.
# ---------------------------------------------------------------------------
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ---------------------------------------------------------------------------
# Application lifecycle events
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """
    Run once when Uvicorn starts the application.
    - Logs key config values so they're visible in container logs.
    - Calls init_db() to create the SQLite tables if they don't exist yet.
    """
    logger.info("Starting Restaurant AI v1.0.0")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Restaurant:  {settings.restaurant_name}")
    logger.info(f"CORS origins: {settings.allowed_origins_list}")

    init_db()
    logger.info("Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Run once when Uvicorn receives a shutdown signal (SIGTERM, Ctrl-C, etc.)."""
    logger.info("Shutting down Restaurant AI")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Root"])
async def root():
    """
    Serve the single-page chat interface.

    Returns the restaurant_chat.html file if it exists.
    Falls back to a JSON status message if the static file is missing
    (useful when running the API without the frontend, e.g. in CI).
    """
    html_file = Path(__file__).parent.parent / "static" / "restaurant_chat.html"
    if html_file.exists():
        return FileResponse(html_file)
    # Fallback: return a JSON object so the API is still usable without the UI
    return {
        "status": "running",
        "restaurant": settings.restaurant_name,
        "message": "Tobi is ready to serve you!",
        "version": "1.0.0",
        "docs": "/api/docs" if settings.is_development else None,
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Lightweight health check endpoint.

    Called every 30 s by Docker's HEALTHCHECK directive (see Dockerfile).
    Also used by external monitoring tools and the app container's depends_on
    condition in docker-compose.yml.
    A non-200 response or timeout causes Docker to mark the container unhealthy.
    """
    return HealthResponse(
        status="healthy",
        environment=settings.environment,
        database="n/a",   # Could be extended to test DB connectivity
        version="1.0.0",
    )


@app.get("/menu", tags=["Menu"])
async def get_menu():
    """
    Return the full menu as a JSON object.

    Called by the frontend on page load to populate the menu modal.
    The structure mirrors MENU_DATA in menu_data.py:
      { "restaurant_name": str, "starters": [...], "mains": [...], ... }
    """
    logger.debug("Menu requested")
    return MENU_DATA


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest, db: ORMSession = Depends(get_db)):
    """
    Main chat endpoint — the heart of the application.

    Steps:
      1. Validate the request (done automatically by Pydantic / FastAPI).
      2. Create or look up the conversation session in the DB.
      3. Persist the user's message to the DB.
      4. Call get_ai_response_with_context() which:
           a. Fetches the last 10 messages from the DB for context.
           b. Sends them + the current message to the Llama-3 model.
           c. Falls back to keyword templates if the AI is unavailable.
      5. Persist Tobi's reply to the DB.
      6. Return the reply in a ChatResponse.

    Args:
        request: Validated ChatRequest (message + optional session_id).
        db:      SQLAlchemy session injected by Depends(get_db).

    Returns:
        ChatResponse with Tobi's reply, the session_id, and the restaurant name.

    Raises:
        HTTPException 500 if anything unexpected goes wrong.
    """
    try:
        # Step 2: Resolve session
        # Use the client-supplied session_id if present, otherwise create a new UUID.
        # This lets the frontend maintain continuity across page refreshes by storing
        # the session_id in localStorage.
        session_id = request.session_id or str(uuid.uuid4())
        session = db.query(DBSession).filter(DBSession.id == session_id).first()

        if not session:
            session = DBSession(id=session_id)
            db.add(session)
            db.commit()
            logger.info(f"Created new session: {session_id}")
        else:
            # Bump updated_at so we know when the session was last active
            session.updated_at = datetime.utcnow()
            db.commit()

        # Step 3: Persist the user's message BEFORE calling the AI so that if
        # the AI call is slow or fails, the message is not lost.
        user_message = DBMessage(
            session_id=session.id,
            role="user",
            content=request.message,
        )
        db.add(user_message)
        db.commit()

        # Step 4: Get Tobi's response (AI with history, or template fallback)
        ai_response = await get_ai_response_with_context(
            request.message,
            session.id,
            db,
        )

        # Step 5: Persist Tobi's reply
        assistant_message = DBMessage(
            session_id=session.id,
            role="assistant",
            content=ai_response,
        )
        db.add(assistant_message)
        db.commit()

        logger.info(
            f"Chat — session={session.id[:8]}... "
            f"user='{request.message[:50]}' "
            f"reply='{ai_response[:50]}'"
        )

        # Step 6: Return the response
        return ChatResponse(
            response=ai_response,
            session_id=session.id,
            restaurant=settings.restaurant_name,
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.get("/chat/history/{session_id}", tags=["Chat"])
async def get_chat_history(session_id: str, db: ORMSession = Depends(get_db)):
    """
    Return the full message history for a session.

    Called by the frontend on page load to restore the conversation if the user
    has already chatted before (their session_id is stored in localStorage).

    Args:
        session_id: The UUID of the session whose history to retrieve.
        db:         SQLAlchemy session injected by Depends(get_db).

    Returns:
        A list of message dicts:
          [{"role": "user"|"assistant", "content": str, "timestamp": ISO-8601 str}, ...]
        Returns an empty list [] if no messages exist for the session.

    Raises:
        HTTPException 500 on unexpected DB errors.
    """
    try:
        messages = (
            db.query(DBMessage)
            .filter(DBMessage.session_id == session_id)
            .order_by(DBMessage.timestamp)   # Ascending — oldest message first
            .all()
        )

        if not messages:
            logger.info(f"No history for session: {session_id[:8]}...")
            return []

        logger.info(f"Retrieved {len(messages)} messages for session: {session_id[:8]}...")

        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in messages
        ]

    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}")


# ---------------------------------------------------------------------------
# Direct execution entry point
# ---------------------------------------------------------------------------
# Allows running with: python -m app.main  (for local dev without Docker)
# In production, Uvicorn is started via the Dockerfile CMD instead.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("Starting Tobi's Restaurant AI...")
    logger.info(f"Server: http://{settings.host}:{settings.port}")
    logger.info(f"Environment: {settings.environment}")
    logger.info("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,        # Auto-reload on code changes in dev
        log_level=settings.log_level.lower(),
    )
