# Design Guide — Tobi Restaurant AI Chatbot

This document is for an engineer building this project from scratch, picking it
up after a gap, or planning a significant extension.  It explains *why* every
major decision was made, not just what the code does.  For a file-by-file tour,
see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## What This App Does

Tobi is a browser-based ordering assistant for *The Common House* restaurant.
A customer visits the web app, chats with Tobi (a surfer-dude AI persona), asks
about the menu, and gets recommendations.  The original design constraint was
**self-contained deployment** — one EC2 instance, no third-party AI APIs, no
external databases, no cloud dependencies.  Everything runs inside Docker Compose.

That constraint is relaxing.  AWS Bedrock is now a supported AI backend for
engineers who want Claude-quality responses without a 9 GB model file.

---

## Tech Stack and Why Each Choice Was Made

### FastAPI
Async Python web framework.  Chosen because:
- Native `async/await` support lets the app handle multiple concurrent requests
  without blocking while waiting for the AI model to respond (which can take 5–60 s).
- Auto-generates OpenAPI docs at `/api/docs` from type annotations — no separate
  Swagger YAML to maintain.
- Pydantic validation is built in — bad request bodies are rejected with a clear
  error before touching business logic.

### pydantic-settings
Loads environment variables into a typed `Settings` object.  Misconfiguration
(wrong type, missing required value) raises an error at **startup**, not buried
in a runtime exception hours later.  All config in one place (`app/config.py`).

### SQLAlchemy + SQLite
Conversation history must survive container restarts — in-memory state would
be wiped on every deploy.  SQLite is file-based (no server process), requires
zero ops overhead, and the file is bind-mounted to the host so it persists.

**Upgrade path:** changing `SQLALCHEMY_DATABASE_URL` to a PostgreSQL connection
string in `app/database.py` is the only code change needed to migrate.  Add
Alembic for schema migrations when you make that switch.

### httpx
Async HTTP client for calling the llama-server container.  Using the standard
`requests` library inside an `async def` endpoint would block the event loop
for the entire 60-second AI timeout, making the app unresponsive to other
requests during that window.  httpx is the async equivalent.

### llama-cpp-python (llama-server)
Runs a quantized GGUF model on CPU with no GPU required, and exposes an
OpenAI-compatible `/v1/chat/completions` endpoint.  That endpoint format is the
same format used by AWS Bedrock's Converse API and the real OpenAI API, so
switching AI backends requires changing only the HTTP target URL and credentials
— the message array structure stays the same.

### Docker Compose
Two-service topology: `app` (FastAPI) and `llama-server` (model inference).
Compose manages the startup dependency (`app` waits for `llama-server` to pass
its health check) and volume mounts for data persistence.  The Bedrock override
(`docker-compose.bedrock.yml`) removes the `llama-server` service entirely with
one command-line flag.

---

## Project Layout

```
restaurant-ai-chatbot/
│
├── app/                   All server-side Python — structured as a package so
│                          internal imports work with `from .module import ...`
│   ├── main.py            FastAPI app + all HTTP endpoints.  The only file that
│   │                      should import from all other modules.
│   ├── config.py          Single Settings object read from env vars.  Import the
│   │                      `settings` singleton everywhere — never re-instantiate.
│   ├── models.py          Two layers: Pydantic models (API boundary) and
│   │                      SQLAlchemy models (DB persistence).  Kept together
│   │                      so the shape of "a message" is defined in one place.
│   ├── database.py        Engine, session factory, and `get_db()` dependency.
│   │                      The only file that knows the DB URL.
│   ├── tobi_ai.py         All AI logic: three (soon four) response modes and
│   │                      the menu keyword search.  main.py calls one function
│   │                      here and doesn't care which backend runs.
│   ├── prompts.py         Tobi's system prompt and few-shot examples.  Separated
│   │                      from tobi_ai.py so non-engineers can edit the
│   │                      personality without touching network call code.
│   └── menu_data.py       The menu.  Single source of truth consumed by the API,
│                          the AI prompt, and the template fallback search.
│
├── static/
│   └── restaurant_chat.html   Complete single-page chat UI.  No build step,
│                              no npm, no CDN.  JS and CSS are inline.
│
├── tests/                 pytest tests.  test_main.py covers endpoints;
│                          test_tobi_ai.py covers chatbot logic.
│
├── scripts/               EC2 provisioning and smoke-test scripts.
│
├── data/                  SQLite DB file (git-ignored, created at runtime,
│                          bind-mounted so it persists across container restarts).
│
├── logs/                  App log file (git-ignored, bind-mounted).
│
├── models/                GGUF model file — too large for git (4.9 GB).
│                          Download once; bind-mounted read-only into llama-server.
│
├── Dockerfile             Multi-stage build for the FastAPI app.
│                          Non-root user, minimal surface area.
│
├── Dockerfile.llama-server  Separate image — includes gcc/g++ needed to compile
│                            llama-cpp-python.  Kept separate so the app image
│                            stays small (~200 MB vs. ~2 GB with build tools).
│
├── docker-compose.yml     Base config: both services, volumes, health checks.
│
├── docker-compose.bedrock.yml  Override: Bedrock mode, no llama-server.
│
├── ARCHITECTURE.md        File-by-file code tour.
├── BEDROCK_INTEGRATION.md Step-by-step AWS Bedrock setup guide.
└── DESIGN_GUIDE.md        ← You are here.
```

---

## Key Design Decisions with Rationale

### 1. Three-mode fallback chain (template → llama → template)

**Problem:** The Llama-3 model takes ~15 minutes to load into RAM on first boot
with `--use_mmap false`.  A hard dependency on the AI would make the app
completely unusable during that window and on underpowered machines.

**Decision:** The app always has a working response available.  Three modes form
a fallback chain:

1. AI with history (primary) — best response quality
2. AI without history (legacy) — same model, simpler call
3. Template fallback (always available) — keyword matching, instant

Any AI error (timeout, connection refused, empty response) silently falls back
to templates.  Tobi never goes silent.

**Trade-off:** Template responses are less natural than LLM responses.  The
`find_menu_item()` function and `food_mappings` dict bridge this gap for the
most common queries (menu lookups, recommendations, prices).

### 2. SQLite, not in-memory state

**Problem:** Conversation context (the last 10 messages) must survive an app
container restart, a deploy, or a brief OOM kill — any of which reset in-memory
state.

**Decision:** Every message is written to SQLite immediately after it is received.
The DB file is bind-mounted to the host so restarts don't lose history.

**Trade-off:** Every chat request does a DB read (last 10 messages) plus two DB
writes (user message, assistant message).  At single-instance scale this is
negligible.  If you scale horizontally, replace SQLite with PostgreSQL.

### 3. System prompt in `prompts.py`, not in `tobi_ai.py`

**Problem:** The system prompt (Tobi's personality, rules, few-shot examples) is
content, not code.  Embedding it in `tobi_ai.py` mixes concerns.

**Decision:** `prompts.py` owns the prompt template.  `tobi_ai.py` calls
`get_system_prompt()` and passes the result to the AI.  A content editor can
iterate on Tobi's personality without reading network call code.

### 4. OpenAI message format throughout

**Problem:** Different AI backends use different request formats.

**Decision:** The codebase uses the OpenAI `[{role, content}]` messages array
everywhere:
- llama-server exposes `/v1/chat/completions` (OpenAI-compatible)
- AWS Bedrock Converse API uses the same `{role, content}` structure
- If you ever switch to the real OpenAI API, the messages array is identical

The only thing that changes between backends is the HTTP target and the content
block format (Bedrock requires `content: [{text: "..."}]` instead of
`content: "..."`).  The dispatcher in `tobi_ai.py` handles this difference.

### 5. Session ID generated client-side

**Problem:** If the server generates session IDs, a user with two browser tabs
would share a session and mix up conversation context.

**Decision:** The frontend generates a UUID with `crypto.randomUUID()` and stores
it in `localStorage`.  Each tab gets its own UUID.  The server accepts whatever
UUID the client sends (creating a new session if it doesn't exist).

**Implication:** Clearing `localStorage` or opening a private browsing tab
always starts a fresh conversation.  This is intentional.

### 6. `USE_LOCAL_AI` boolean → `AI_BACKEND` string

**Current state:** `USE_LOCAL_AI: bool` is a 2-state switch: AI or template.

**Why it needs to change:** Adding Bedrock as a third option breaks the boolean
model.  Three states require a string enum: `"template"` / `"llama"` / `"bedrock"`.

**Migration strategy:**
- The new `ai_backend: str` field takes precedence when set.
- Existing deployments that set `USE_LOCAL_AI=true` still work — the dispatcher
  falls back to reading `use_local_ai` when `ai_backend` is not set.
- No flag day.  Both fields coexist permanently.

---

## Setting Up From Zero

### Template mode (instant, no model, no AWS)

```bash
git clone https://github.com/Erics38/restaurant-ai-chatbot.git
cd restaurant-ai-chatbot
cp .env.example .env
# Edit .env: set SECRET_KEY, confirm AI_BACKEND=template
docker compose up --build
# Ready in ~10 seconds. Visit http://localhost:8000
```

### Local Llama-3 mode (~9 GB RAM, ~15 min first boot)

```bash
# 1. Download the model (4.9 GB):
#    See scripts/ec2-setup-with-ai.sh for the HuggingFace URL.
#    Place at: ./models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf

# 2. Configure
cp .env.example .env
# Edit .env: set USE_LOCAL_AI=true, SECRET_KEY

# 3. Start (first boot takes ~15 min while model loads into RAM)
docker compose up --build

# Watch model loading:
docker compose logs -f llama-server
# Ready when you see: "HTTP server listening at http://0.0.0.0:8080"
```

### AWS Bedrock mode (no local model, pay-per-token)

```bash
# 1. Complete BEDROCK_INTEGRATION.md Steps 1 and 2

# 2. Configure
cp .env.example .env
# Edit .env: set AI_BACKEND=bedrock, AWS_REGION, BEDROCK_MODEL_ID, SECRET_KEY

# 3. Start (app ready in ~10 seconds — no model to load)
docker compose -f docker-compose.yml -f docker-compose.bedrock.yml up --build
```

---

## How to Extend

### Add a new AI backend

The dispatcher pattern in `tobi_ai.py` is designed for this.

1. **`app/config.py`** — add new fields to `Settings` (API URL, credentials, etc.)
2. **`app/tobi_ai.py`** — add a new `get_<backend>_response_with_context()` function
3. **`app/tobi_ai.py`** — add a new branch in `get_response_with_context()` dispatcher
4. **`docker-compose.<backend>.yml`** — create an override if the backend changes the service topology
5. **`app/main.py`** — no changes needed (calls the dispatcher, not backend functions directly)
6. **`app/prompts.py`** — no changes needed
7. **`app/models.py`** — no changes needed

### Add a new API endpoint

1. Define Pydantic request/response models in `app/models.py` (if needed)
2. Add the endpoint function to `app/main.py`
3. Add tests in `tests/test_main.py`

### Change the menu

Edit `app/menu_data.py` only.  The `MENU_DATA` dict is the single source of truth.
Changes propagate automatically to:
- `GET /menu` endpoint (returned directly)
- AI system prompt (injected by `prompts.py`)
- Template fallback search (`find_menu_item()` in `tobi_ai.py`)
- Frontend menu modal (loaded from the API on page load)

No other files need touching.

### Change Tobi's personality or rules

Edit `SYSTEM_PROMPT_TEMPLATE` in `app/prompts.py`.

- To make Tobi more formal: update the `PERSONALITY` block
- To add new rules (e.g., "always mention allergens"): add to the `RULES` block
- To improve model consistency: add concrete examples to the `EXAMPLES` block

The template fallback (`get_tobi_response()`) has its own hardcoded responses
in `TOBI_RESPONSES` at the top of `tobi_ai.py` — edit those separately.

---

## Configuration Reference

| Variable | Default | When to change |
|----------|---------|----------------|
| `ENVIRONMENT` | `development` | Set `production` to disable Swagger UI |
| `HOST` | `0.0.0.0` | Rarely — only if binding to a specific interface |
| `PORT` | `8000` | If 8000 is in use |
| `RESTAURANT_NAME` | `The Common House` | If rebranding or white-labelling |
| `USE_LOCAL_AI` | `false` | `true` to use Llama-3 (legacy; prefer `AI_BACKEND`) |
| `LLAMA_SERVER_URL` | `None` | Set to `http://llama-server:8080` in Docker |
| `AI_BACKEND` | `template` | `llama` or `bedrock` when implementing AI |
| `AWS_REGION` | `us-east-1` | Change if deploying to a different region |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Pin to approved model version |
| `SECRET_KEY` | dev placeholder | **Always change in production** |
| `ALLOWED_ORIGINS` | `*` | Restrict to your domain in production |
| `LOG_LEVEL` | `INFO` | `DEBUG` for troubleshooting |
| `LOG_FILE` | `logs/app.log` | Rarely needs changing |

---

## Operational Gotchas

**Cold start is 15 minutes in Llama mode.**
`llama-server` loads the entire 4.9 GB model into RAM before accepting requests.
The docker-compose.yml health check `start_period: 900s` accounts for this.
Do not reduce it without testing on your target instance type.

**The SQLite database grows indefinitely.**
There is no session cleanup job.  On a long-running deployment, `data/conversations.db`
will grow without bound.  Add a cron job to delete sessions older than N days
using SQLAlchemy's `delete()` on `DBSession` where `updated_at < threshold`.

**The `./app` volume mount enables hot reload — remove it in production.**
In `docker-compose.yml`, the `- ./app:/app/app` volume mount lets you edit Python
files and see changes without rebuilding.  It also means the production container
runs whatever is on disk, bypassing the built image.  Comment it out for production.

**New AWS accounts have very low Bedrock quotas.**
Default is 2–3 requests per minute for Claude Sonnet on new accounts.  For a
low-traffic restaurant chatbot this is usually enough, but request a quota increase
through AWS Support before launch if you expect concurrent users.

**`depends_on` in the Bedrock override must be `{}`, not omitted.**
Omitting `depends_on` from the override file causes Docker Compose to inherit the
base file's `depends_on: { llama-server: { condition: service_healthy } }`.  The
app then waits indefinitely for a container that never starts.  The explicit
empty mapping `{}` is required to clear the dependency.
