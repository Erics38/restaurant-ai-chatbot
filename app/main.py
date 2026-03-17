"""
Restaurant AI - FastAPI Application
Main application with all endpoints, logging, and error handling.
"""

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .models import ChatRequest, ChatResponse, HealthResponse
from .tobi_ai import get_tobi_response_async
from .menu_data import MENU_DATA

# ===== Logging Configuration =====
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(settings.log_file), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

# ===== FastAPI Application =====
app = FastAPI(
    title="Restaurant AI",
    description="The Common House - AI-powered restaurant ordering system",
    version="1.0.0",
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url="/api/redoc" if settings.is_development else None,
)

# ===== CORS Middleware =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Static Files =====
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ===== Startup/Shutdown Events =====
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting Restaurant AI v1.0.0")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.database_url}")
    logger.info(f"CORS Origins: {settings.allowed_origins_list}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down Restaurant AI")


# ===== API Endpoints =====


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with basic info."""
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
    Health check endpoint for monitoring.
    Used by Docker, Kubernetes, load balancers, etc.
    """
    db_status = "connected" if db.health_check() else "disconnected"

    if db_status == "disconnected":
        logger.warning("Health check failed: Database disconnected")
        raise HTTPException(status_code=503, detail="Database unavailable")

    return HealthResponse(status="healthy", environment=settings.environment, database=db_status, version="1.0.0")


@app.get("/menu", tags=["Menu"])
async def get_menu():
    """Get the full restaurant menu."""
    logger.debug("Menu requested")
    return MENU_DATA


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Chat with Tobi, the AI assistant.

    - **message**: Customer's message (1-500 characters)
    - **session_id**: Optional session identifier
    """
    try:
        # Generate or use provided session ID
        session_id = request.session_id or str(uuid.uuid4())

        # Get Tobi's response (async)
        ai_response = await get_tobi_response_async(request.message)

        logger.info(f"Chat - Session: {session_id[:8]}... | VIP: {has_magic_password}")

        return ChatResponse(
            response=ai_response,
            session_id=session_id,
            restaurant=settings.restaurant_name,
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")




# ===== Main Entry Point =====
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
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
