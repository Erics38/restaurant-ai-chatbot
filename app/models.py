"""
Pydantic models for request/response validation.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ===== Menu Models =====
class MenuItem(BaseModel):
    """A single menu item."""

    name: str
    description: str
    price: float = Field(gt=0, description="Price must be positive")


class MenuCategory(BaseModel):
    """Menu items organized by category."""

    starters: list[MenuItem]
    mains: list[MenuItem]
    desserts: list[MenuItem]
    drinks: list[MenuItem]


# ===== Chat Models =====
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., min_length=1, max_length=500, description="Customer message")
    session_id: Optional[str] = Field(None, description="Session identifier")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str
    session_id: str
    restaurant: str


# ===== Health Check =====
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    environment: str
    database: str
    version: str = "1.0.0"
