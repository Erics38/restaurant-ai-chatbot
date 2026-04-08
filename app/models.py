"""
Data models for the Restaurant AI Chatbot.

This file contains two distinct kinds of models that serve different purposes:

  1. Pydantic models  — used at the API boundary.
     FastAPI uses these to validate incoming JSON, coerce types, and serialise
     outgoing responses.  They live only in memory (not in the database).

  2. SQLAlchemy ORM models — used to persist data to SQLite.
     These map directly to database tables.  They are never returned from the
     API directly; instead they are read from the DB and converted to Pydantic
     models before being sent to the client.

Keeping these two layers separate is intentional: it lets the DB schema and the
API contract evolve independently.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


# ===========================================================================
# Pydantic — Menu models (used by GET /menu)
# ===========================================================================

class MenuItem(BaseModel):
    """
    A single dish or drink on the menu.
    Returned as part of the /menu response so the frontend can render the menu modal.
    """
    name: str
    description: str
    price: float = Field(gt=0, description="Price in USD; must be a positive number")


class MenuCategory(BaseModel):
    """
    The full menu grouped into four categories.
    Not currently used as a response model directly (the raw dict from menu_data.py
    is returned instead), but useful for validation and documentation.
    """
    starters: list[MenuItem]
    mains: list[MenuItem]
    desserts: list[MenuItem]
    drinks: list[MenuItem]


# ===========================================================================
# Pydantic — Chat models (used by POST /chat and GET /chat/history)
# ===========================================================================

class ChatRequest(BaseModel):
    """
    Payload the frontend sends when the user submits a message.

    Fields:
      message    — The user's text. Capped at 500 chars to prevent abuse.
      session_id — Optional UUID that ties messages together into a conversation.
                   If omitted, the backend generates a new UUID and returns it
                   in the response so the client can store it for future turns.
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Customer's message to Tobi"
    )
    session_id: Optional[str] = Field(
        None,
        description="UUID session identifier; omit to start a new conversation"
    )


class ChatResponse(BaseModel):
    """
    What the backend sends back after processing a chat message.

    Fields:
      response   — Tobi's reply (either from the Llama-3 model or templates).
      session_id — The session UUID; the client should persist this in localStorage
                   so subsequent messages are linked to the same conversation.
      restaurant — Restaurant name pulled from settings, displayed in the UI.
    """
    response: str
    session_id: str
    restaurant: str


# ===========================================================================
# Pydantic — Health check model (used by GET /health)
# ===========================================================================

class HealthResponse(BaseModel):
    """
    Returned by the /health endpoint which is polled by Docker, load balancers,
    and uptime monitors to confirm the service is running.
    """
    status: str        # Always "healthy" when the app is up
    environment: str   # "development" or "production" — from settings
    database: str      # Reserved for future DB connectivity checks
    version: str = "1.0.0"


# ===========================================================================
# SQLAlchemy ORM — Database persistence models
# ===========================================================================

class DBSession(Base):
    """
    Represents a single user conversation session in the database.

    Each browser tab (or each time a user clears their chat) gets a new session.
    The session ID is a UUID generated either by the frontend (crypto.randomUUID)
    or by the backend when none is provided.

    Table: sessions
    """
    __tablename__ = "sessions"

    # UUID string, e.g. "550e8400-e29b-41d4-a716-446655440000"
    id = Column(String(36), primary_key=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    # updated_at is bumped on every new message — useful for finding idle sessions
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One session → many messages.
    # cascade="all, delete-orphan" means deleting a session also deletes all its
    # messages, preventing orphaned rows in the messages table.
    messages = relationship("DBMessage", back_populates="session", cascade="all, delete-orphan")


class DBMessage(Base):
    """
    A single message within a conversation session.

    Stores both sides of the conversation (user + assistant) so the AI can be
    given the last N messages as context on each new request, enabling memory
    across turns.

    Table: messages
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key links this message to its parent session
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)

    # "user" or "assistant" — mirrors the role field in OpenAI-style chat APIs
    role = Column(String(10), nullable=False)

    # The actual message text; TEXT allows unlimited length in SQLite
    content = Column(Text, nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow)

    # Back-reference to the parent DBSession object
    session = relationship("DBSession", back_populates="messages")
