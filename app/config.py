"""
Configuration management for the Restaurant AI Chatbot.

All configuration is loaded from environment variables (and optionally a .env file).
Uses pydantic-settings so every value is type-checked on startup — if a required
env var is missing or the wrong type, the app fails fast with a clear error.

Environment precedence (highest → lowest):
  1. Shell environment variables (e.g. export ENVIRONMENT=production)
  2. .env file in the project root
  3. Default values defined below

To change a setting without editing code, set the corresponding env var.
Example:  RESTAURANT_NAME="Tobi's Grill"  docker compose up
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central settings object — instantiated once at module import time and
    shared across the entire app via `from app.config import settings`.

    All fields map 1-to-1 with an environment variable of the same name
    (case-insensitive). See .env.example for a full list with explanations.
    """

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------
    host: str = "0.0.0.0"   # Bind address; 0.0.0.0 = accept all interfaces
    port: int = 8000
    debug: bool = False       # Enables Uvicorn debug mode (auto-reload etc.)
    environment: str = "development"  # "development" | "production"

    # ------------------------------------------------------------------
    # Restaurant branding
    # ------------------------------------------------------------------
    restaurant_name: str = "The Common House"  # Shown in API responses & UI

    # ------------------------------------------------------------------
    # AI / llama-server integration
    # ------------------------------------------------------------------
    # URL of the llama-cpp-python server container (see docker-compose.yml).
    # When None the app falls back to hard-coded template responses.
    llama_server_url: Optional[str] = None

    # Master switch: set USE_LOCAL_AI=true to route every chat through the
    # Llama-3 model; false = always use fast keyword-template responses.
    use_local_ai: bool = False

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    # Used to sign any future JWT tokens. MUST be changed in production.
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = "dev-secret-key-change-in-production"

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    # Comma-separated list of allowed origins, or "*" to allow all.
    # Example: "https://myrestaurant.com,https://admin.myrestaurant.com"
    allowed_origins: str = "*"

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_level: str = "INFO"          # DEBUG | INFO | WARNING | ERROR | CRITICAL
    log_file: str = "logs/app.log"   # Relative to the working directory

    # Pydantic-settings meta: load .env file, ignore unknown extra vars
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Don't crash if .env has keys we don't know about
    )

    # ------------------------------------------------------------------
    # Computed properties (not settable via env vars)
    # ------------------------------------------------------------------

    @property
    def allowed_origins_list(self) -> list[str]:
        """
        Parse the ALLOWED_ORIGINS string into the list that FastAPI's
        CORSMiddleware expects.
        "*" → ["*"]   (allow everything — fine for local dev, risky in prod)
        "a.com,b.com" → ["a.com", "b.com"]
        """
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_development(self) -> bool:
        """True when ENVIRONMENT=development. Enables /api/docs, auto-reload, etc."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """True when ENVIRONMENT=production. Disables Swagger UI, tightens CORS, etc."""
        return self.environment.lower() == "production"


# ---------------------------------------------------------------------------
# Singleton — import this object everywhere instead of re-instantiating.
# ---------------------------------------------------------------------------
settings = Settings()


def ensure_directories():
    """
    Create the data/, logs/, and models/ directories if they don't already exist.

    Called automatically at import time so the app never crashes because a
    directory is missing.  Docker bind-mounts will create these too, but this
    guard makes local (non-Docker) development work out of the box.
    """
    base_dir = Path(__file__).parent.parent  # Project root (one level above app/)

    directories = [
        base_dir / "data",    # SQLite database files
        base_dir / "logs",    # Application log files
        base_dir / "models",  # GGUF model files for llama-cpp
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Run once when this module is first imported
ensure_directories()
