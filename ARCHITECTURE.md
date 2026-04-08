# Tobi — Restaurant AI Chatbot: Architecture Guide

> This document is for the next developer who picks up this codebase.
> It covers the overall design, how the pieces fit together, and where
> to look when you need to make a change.

---

## Table of Contents

1. [Big Picture](#1-big-picture)
2. [Directory Structure](#2-directory-structure)
3. [Services & Containers](#3-services--containers)
4. [Request Flow](#4-request-flow)
5. [Module Reference](#5-module-reference)
6. [AI Response Modes](#6-ai-response-modes)
7. [Database Schema](#7-database-schema)
8. [Configuration Reference](#8-configuration-reference)
9. [Frontend (Chat UI)](#9-frontend-chat-ui)
10. [Running Locally](#10-running-locally)
11. [Common Tasks](#11-common-tasks)

---

## 1. Big Picture

Tobi is an **AI-powered restaurant ordering assistant** for *The Common House*.
A customer visits the app in a browser, chats with Tobi (a surfer-dude persona),
and can ask about the menu, get recommendations, and place orders.

```
Browser  ──HTTP──►  FastAPI app (port 8000)
                         │
                         ├─ SQLite DB  (conversation history)
                         │
                         └─HTTP──►  llama-server (port 8080)
                                       │
                                       └─  Llama-3-8B model (4.9 GB GGUF)
```

**Two operational modes:**

| Mode | When | Behaviour |
|------|------|-----------|
| AI mode | `USE_LOCAL_AI=true` + model file present | Responses come from Llama-3 with full menu context and conversation memory |
| Template mode | `USE_LOCAL_AI=false` or model missing | Responses are keyword-matched Python templates — fast, no GPU needed |

The app **always falls back to templates** if the AI server is unreachable, times out,
or returns an empty response. Tobi never goes silent.

---

## 2. Directory Structure

```
restaurant-ai-chatbot/
│
├── app/                        Python package — all server-side logic
│   ├── __init__.py             Package version (1.0.0)
│   ├── main.py                 FastAPI app, all endpoints, startup/shutdown hooks
│   ├── config.py               Pydantic-settings: loads env vars, exposes `settings`
│   ├── models.py               Pydantic API models + SQLAlchemy DB models
│   ├── database.py             SQLAlchemy engine, session factory, init_db()
│   ├── tobi_ai.py              AI call logic, template fallback, menu search
│   ├── prompts.py              System prompt template + get_system_prompt()
│   └── menu_data.py            Hardcoded menu (single source of truth)
│
├── static/
│   ├── restaurant_chat.html    Single-page chat UI (HTML + CSS + JS, no build step)
│   └── index.html              Simple redirect index
│
├── tests/
│   ├── conftest.py             Pytest fixtures
│   ├── test_main.py            Endpoint integration tests
│   ├── test_tobi_ai.py         Chatbot logic unit tests
│   ├── test_models.py          Pydantic model validation tests
│   ├── test_docker_health.py   Docker container health tests
│   └── requirements-test.txt  Test-only dependencies
│
├── scripts/
│   ├── ec2-setup-with-ai.sh    Full EC2 Ubuntu setup (installs Docker, downloads model)
│   ├── ec2-user-data.sh        EC2 user-data cloud-init script
│   ├── test-ai-model.sh        Smoke-test the llama-server endpoint
│   └── verify-ci-locally.sh   Run the CI pipeline locally
│
├── data/                       SQLite database (git-ignored, created at runtime)
├── logs/                       App logs (git-ignored, created at runtime)
├── models/                     GGUF model file (git-ignored, too large for git)
│
├── Dockerfile                  Multi-stage build for the FastAPI app
├── Dockerfile.llama-server     Build for the llama-cpp-python inference server
├── docker-compose.yml          Orchestrates both containers
├── requirements.txt            Python runtime dependencies
├── .env.example                Template for the .env file
└── ARCHITECTURE.md             ← You are here
```

---

## 3. Services & Containers

### `app` — FastAPI application

| Property | Value |
|----------|-------|
| Image | Built from `Dockerfile` (Python 3.11-slim, multi-stage) |
| Port | `8000` (external) → `8000` (internal) |
| User | `appuser` (non-root) |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Health check | `GET /health` every 30 s |

**Volume mounts:**

| Host path | Container path | Purpose |
|-----------|----------------|---------|
| `./data`  | `/app/data`    | Persist SQLite DB across restarts |
| `./logs`  | `/app/logs`    | Persist log files |
| `./models`| `/app/models`  | Read-only model files |
| `./app`   | `/app/app`     | Live code reload (dev only — remove in prod) |

### `llama-server` — Llama-3-8B inference server

| Property | Value |
|----------|-------|
| Image | Built from `Dockerfile.llama-server` (Python 3.11-slim + gcc/g++) |
| Port | `8080` (both host and container) |
| User | `llama` (non-root) |
| Start command | `python -m llama_cpp.server --model /models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf ...` |
| Health check | `GET /v1/models` every 30 s, 900 s start period |
| Memory | 7 GB reserved, 9 GB hard limit |
| CPU | 2.0 reserved, 4.0 limit |

> **First boot warning:** `--use_mmap false` forces the entire 4.9 GB model into RAM
> before the server becomes ready. Expect ~15 minutes on a cold EC2 instance.
> Subsequent starts are faster because the OS page cache retains the file.

---

## 4. Request Flow

```
1.  User types a message and clicks Send
         │
         ▼
2.  Frontend (restaurant_chat.html)
    • Reads sessionId from localStorage (or generates a new UUID)
    • POST /chat  { message: "...", session_id: "uuid" }
         │
         ▼
3.  FastAPI — POST /chat  (main.py)
    • Validates request (Pydantic: 1–500 chars)
    • Create or load DBSession from SQLite
    • Insert user DBMessage into SQLite
    • Call get_ai_response_with_context(message, session_id, db)
         │
         ▼
4.  tobi_ai.py — get_ai_response_with_context()
    • Query last 10 DBMessages for this session  (conversation memory)
    • Build messages array:
        [ {role: system, content: <system prompt + full menu>},
          ...last 10 DB messages...,
          {role: user, content: <current message>} ]
    • POST /v1/chat/completions  to llama-server:8080
         │
         ▼  (success)
5.  llama-server
    • Llama-3-8B model generates a response
    • Returns { choices: [{ message: { content: "..." } }] }
         │
         ▼  (or error/timeout → fallback)
    tobi_ai.py — get_tobi_response()
    • Keyword match + template lookup (always available)
         │
         ▼
6.  Back in main.py
    • Insert assistant DBMessage into SQLite
    • Return ChatResponse { response, session_id, restaurant }
         │
         ▼
7.  Frontend
    • Display Tobi's bubble
    • Store sessionId in localStorage for next message
```

---

## 5. Module Reference

### `app/config.py`

Single `Settings` class (Pydantic-settings) that reads from environment variables
and the `.env` file.  A singleton `settings` object is imported everywhere:

```python
from app.config import settings
print(settings.restaurant_name)   # "The Common House"
print(settings.is_production)     # True / False
```

To add a new config value: add a typed field to `Settings` and document it
in `.env.example`.

---

### `app/database.py`

Sets up the SQLAlchemy engine and session factory for SQLite.

Key exports:
- `Base` — declarative base; all models inherit from this
- `get_db()` — FastAPI dependency; yields one DB session per request
- `init_db()` — creates all tables on startup (idempotent)

To switch to PostgreSQL: change `SQLALCHEMY_DATABASE_URL` and remove
`check_same_thread=False` from `connect_args`.

---

### `app/models.py`

Two layers in one file:

**Pydantic models** (API validation / serialisation):
- `ChatRequest` — incoming POST /chat body
- `ChatResponse` — outgoing POST /chat response
- `HealthResponse` — GET /health response
- `MenuItem`, `MenuCategory` — menu shape (used for docs/typing)

**SQLAlchemy models** (database persistence):
- `DBSession` — one row per conversation (keyed by UUID)
- `DBMessage` — one row per message (user or assistant)

---

### `app/menu_data.py`

The single source of truth for all menu items.  The `MENU_DATA` dict is
consumed by:
- `GET /menu` (returned directly to the frontend)
- `prompts.py` (injected into the system prompt for the AI)
- `tobi_ai.py` (searched by keyword in template fallback mode)

**To add a menu item:** append a dict to the appropriate category list.
No other files need changing.

---

### `app/prompts.py`

Contains `SYSTEM_PROMPT_TEMPLATE` (Tobi's personality, rules, and few-shot
examples) and `get_system_prompt(include_menu=True)` which injects the
live menu at call time.

The system prompt is sent as the first message in every AI request.
Edit this file to change Tobi's personality or add/remove few-shot examples.

---

### `app/tobi_ai.py`

The chatbot engine.  Three functions, used as a fallback chain:

| Function | Mode | When used |
|----------|------|-----------|
| `get_ai_response_with_context` | AI + history | Primary — called by main.py |
| `get_ai_response` | AI, no history | Via `get_tobi_response_async` (legacy) |
| `get_tobi_response` | Templates | Fallback when AI unavailable |

Also contains `find_menu_item(query)` which searches `MENU_DATA` using
direct string matching and a `food_mappings` dictionary for semantic expansion
("pasta" → pappardelle, spaghetti, mac).

---

### `app/main.py`

FastAPI application.  Registers all endpoints and lifecycle events.
The only file that should import from all other modules.

Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve `restaurant_chat.html` |
| GET | `/health` | Health check |
| GET | `/menu` | Return `MENU_DATA` |
| POST | `/chat` | Chat with Tobi |
| GET | `/chat/history/{session_id}` | Retrieve message history |

---

## 6. AI Response Modes

### Mode 1 — AI with conversation history (primary)

Called by `main.py` every time a message is received.

```
messages = [
  { role: "system",    content: get_system_prompt(include_menu=True) },  # ~600 tokens
  { role: "user",      content: "Hi there" },          # message N-9
  { role: "assistant", content: "Hey dude! ..." },      # message N-8
  ...                                                    # last 10 messages
  { role: "user",      content: "What's your burger?" } # current message
]
POST http://llama-server:8080/v1/chat/completions
  max_tokens:  150
  temperature: 0.6
  stop:        ["\n\n", "Customer:", "User:"]
```

**Why 10 messages?** The Llama-3-8B context window is 4096 tokens.
The system prompt uses ~600, leaving ~3400 for history + response.
10 short messages typically fit well within that budget.

**Why temperature 0.6?** Lower values (closer to 0) make the model more
deterministic and consistent in personality.  Higher values make it more
creative but also more likely to break character.

### Mode 3 — Template fallback

`get_tobi_response()` checks the message against these patterns in order:

1. Greeting (≤3 words containing hi/hello/hey/sup/yo)
2. Menu item match via `find_menu_item()`
3. General menu question (contains "menu", "what do you have", etc.)
4. Recommendation request (contains "recommend", "suggest", "best", etc.)
5. Price question (contains "price", "cost", "how much", etc.)
6. Default catch-all

---

## 7. Database Schema

SQLite file: `data/conversations.db`

```sql
CREATE TABLE sessions (
    id         TEXT PRIMARY KEY,   -- UUID, e.g. "550e8400-..."
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role       TEXT NOT NULL,      -- "user" or "assistant"
    content    TEXT NOT NULL,
    timestamp  DATETIME
);
```

- Deleting a session cascades to delete all its messages.
- `updated_at` on sessions is bumped on each new message (useful for pruning old sessions).
- There is currently no cleanup job — the DB will grow indefinitely.
  Consider adding a scheduled task to delete sessions older than N days.

---

## 8. Configuration Reference

Set these as environment variables or in a `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | `development` or `production`. Controls whether Swagger UI is enabled. |
| `HOST` | `0.0.0.0` | Bind address for Uvicorn |
| `PORT` | `8000` | Listen port |
| `RESTAURANT_NAME` | `The Common House` | Shown in API responses and the browser title |
| `USE_LOCAL_AI` | `false` | `true` → use Llama-3; `false` → template-only mode |
| `LLAMA_SERVER_URL` | *(none)* | URL of the llama-cpp server, e.g. `http://llama-server:8080` |
| `SECRET_KEY` | `dev-secret-key-...` | For future JWT signing. Change in production. |
| `ALLOWED_ORIGINS` | `*` | CORS origins. Restrict in production, e.g. `https://myrestaurant.com` |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `LOG_FILE` | `logs/app.log` | Path for the file log handler |

---

## 9. Frontend (Chat UI)

`static/restaurant_chat.html` is a self-contained SPA — no npm, no build, no CDN.

**Startup sequence (window load):**
1. `initializeSession()` — read/create UUID in `localStorage`
2. `loadMenu()` — fetch `/menu`, render modal, enable input
3. `loadConversationHistory()` — fetch `/chat/history/{sessionId}`, render bubbles

**Per-message flow:**
1. User types and hits Enter or Send
2. `sendMessage(event)` appends the user bubble immediately
3. Shows loading indicator ("Tobes is thinking...")
4. `POST /chat` with `{ message, session_id }`
5. Hides loading indicator, appends Tobi's bubble

**Session persistence:**  
The session UUID is stored in `localStorage` under the key `restaurantSessionId`.
Clearing localStorage (or clicking "Clear Chat") starts a new session.

---

## 10. Running Locally

### Full AI mode (requires ~10 GB RAM)

```bash
# 1. Place model file in ./models/
#    Download: see scripts/ec2-setup-with-ai.sh for the HuggingFace URL

# 2. Create .env
cp .env.example .env
# Edit .env: set SECRET_KEY, set USE_LOCAL_AI=true

# 3. Start
docker compose up --build

# First boot takes ~15 min while the model loads. Watch logs:
docker compose logs -f llama-server
```

### Template-only mode (fast, no model needed)

```bash
USE_LOCAL_AI=false docker compose up --build
# Ready in ~10 seconds
```

### Without Docker (development)

```bash
pip install -r requirements.txt
ENVIRONMENT=development LLAMA_SERVER_URL=http://localhost:8080 uvicorn app.main:app --reload
```

### Running tests

```bash
pip install -r tests/requirements-test.txt
pytest tests/ -v
```

---

## 11. Common Tasks

### Change the restaurant name

Set `RESTAURANT_NAME` in `.env` or `docker-compose.yml`.
The name flows through to API responses and is embedded in Tobi's system prompt.

### Add a menu item

Edit `app/menu_data.py` — append to the relevant category list:
```python
{"name": "New Dish", "description": "Ingredients here", "price": 18.00},
```
The change is picked up automatically by the API, the menu modal, the AI
system prompt, and the template fallback search.

### Change Tobi's personality

Edit `SYSTEM_PROMPT_TEMPLATE` in `app/prompts.py`.
Add more few-shot examples to the `EXAMPLES` block to steer the model's behaviour.

### Add a new API endpoint

1. Define request/response Pydantic models in `app/models.py` (if needed).
2. Add the endpoint function in `app/main.py`.
3. Add tests in `tests/test_main.py`.

### Switch from SQLite to PostgreSQL

1. Change `SQLALCHEMY_DATABASE_URL` in `app/database.py`.
2. Remove `connect_args={"check_same_thread": False}` from `create_engine()`.
3. Add `psycopg2-binary` to `requirements.txt`.
4. Run Alembic migrations instead of relying on `create_all`.

### Deploy to EC2

See `scripts/ec2-setup-with-ai.sh` for the full automated setup.
See `DEPLOYMENT.md` for a step-by-step guide.

---

*Last updated: April 2026*
