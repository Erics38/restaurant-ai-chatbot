# Restaurant AI — The Common House

A local AI-powered restaurant ordering system. Tobi, the chatbot, knows the full menu and handles order management. Built with FastAPI and a local Phi-2 model.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI Status](https://github.com/Erics38/restaurant-ai-chatbot/actions/workflows/ci.yml/badge.svg)](https://github.com/Erics38/restaurant-ai-chatbot/actions/workflows/ci.yml)
[![Docker Build](https://github.com/Erics38/restaurant-ai-chatbot/actions/workflows/docker.yml/badge.svg)](https://github.com/Erics38/restaurant-ai-chatbot/actions/workflows/docker.yml)

---

## Relevance to SaaS & Technical Roles

This project demonstrates patterns used in modern SaaS platforms. Solutions Engineers and Onboarding Specialists work with these daily:

- **Conversational AI integration** — Intercom, Drift, and Help Scout use similar chatbot flows for customer onboarding
- **Self-documented REST API** — Swagger and ReDoc enable enterprise customers to integrate without hand-holding
- **Environment-based configuration** — Multi-tenant SaaS applications use `.env` files for deployment flexibility
- **Docker containerization** — Technical teams guide customers through containerized deployments and upgrades
- **CI/CD pipeline** — Software delivery automation runs behind every SaaS product

---

## Features

- **Menu-Aware Chatbot** — Tobi knows food categories, ingredients, and can recommend items
- **Local AI Model** — Phi-2 runs locally for natural language understanding (2-10s response time)
- **Template Fallback** — Instant responses (<10ms) when AI is unavailable or disabled
- **Full Menu System** — Starters, mains, desserts, and drinks
- **Order Management** — Track orders using presidential birth year order numbers
- **Magic Password** — VIP treatment for customers who say "i'm on yelp"
- **SQLite Database** — Persistent order storage
- **Production Ready** — Logging, health checks, and error handling
- **Docker Support** — One-command deployment
- **Environment Configuration** — Configure via `.env` files
- **Zero API Costs** — No external dependencies or API fees

---

## Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User's Browser                          │
│                  http://localhost:8000/static/                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Restaurant AI (FastAPI)                      │
│                         Port 8000                               │
├─────────────────────────────────────────────────────────────────┤
│  Endpoints:                                                     │
│  • GET  /                    - Root/Health                      │
│  • GET  /menu                - Menu data                        │
│  • POST /chat                - Chat with Tobi                   │
│  • POST /order               - Create order                     │
│  • GET  /order/{id}          - Get order status                 │
└────────────┬───────────────────────────────┬────────────────────┘
             │                               │
             ▼                               ▼
┌──────────────────────┐    ┌────────────────────────────────────┐
│   SQLite Database    │    │   llama-server (Optional)          │
│   (data/orders.db)   │    │   Port 8080                        │
└──────────────────────┘    └────────────────────────────────────┘
```

---

## Quick Start

**Prerequisites:** Docker and 1.7 GB of disk space for the Phi-2 model

### Step 1: Download Model (one-time setup)

```bash
mkdir -p models
curl -L -o models/phi-2.Q4_K_M.gguf \
  https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf
```

### Step 2: Start with Docker

```bash
# Windows:
start.bat

# macOS/Linux:
chmod +x start.sh && ./start.sh

# Or manually:
docker-compose up --build -d
```

**Access:** http://localhost:8000/static/restaurant_chat.html

### Optional: Fast Template Mode (No AI)

```bash
USE_LOCAL_AI=false docker-compose up -d
```

---

## Project Structure

```
restaurant-ai/
├── app/
│   ├── main.py          # FastAPI application & endpoints
│   ├── config.py        # Environment-based configuration
│   ├── models.py        # Pydantic models for validation
│   ├── database.py      # SQLite database operations
│   ├── tobi_ai.py       # AI chatbot logic (menu-aware)
│   └── menu_data.py     # Restaurant menu data
├── static/
│   └── restaurant_chat.html  # Web interface
├── tests/               # Unit tests
├── .env.example         # Environment variable template
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Configuration

Copy `.env.example` to `.env` and update as needed:

```bash
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
DATABASE_URL=sqlite:///./data/orders.db
RESTAURANT_NAME=The Common House
ENABLE_MAGIC_PASSWORD=True
MAGIC_PASSWORD=i'm on yelp
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Root endpoint with basic info |
| `GET`  | `/health` | Health check for monitoring |
| `GET`  | `/menu` | Get full restaurant menu |
| `POST` | `/chat` | Chat with Tobi AI |
| `POST` | `/order` | Create a new order |
| `GET`  | `/order/{order_number}` | Get order details |

- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc

---

## Chat Examples

```bash
# Ask about menu items
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What burgers do you have?"}'

# Get a recommendation
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What do you recommend?"}'
```

---

## Testing

```bash
pytest
black app/
flake8 app/
mypy app/
```

---

## Docker Commands

```bash
docker-compose up --build    # Build and start
docker-compose up -d         # Run in background
docker-compose logs -f app   # View logs
docker-compose down          # Stop
```

---

## Documentation

- **[SETUP.md](SETUP.md)** — Complete setup guide for new users
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Production deployment guide
- **[CICD.md](CICD.md)** — CI/CD pipeline documentation
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** — Upgrading from previous versions
- **[DOCKER_QUICK_START.md](DOCKER_QUICK_START.md)** — Fast Docker reference

---

## Contributing

We welcome contributions! The project uses GitHub Actions for CI/CD to ensure code quality.

### Quick Start for Contributors

1. **Fork and clone** the repository
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Install dev tools**: `pip install pytest pytest-asyncio black flake8 mypy`
4. **Run verification**: `./scripts/verify-ci-locally.sh` (or `.bat` on Windows)
5. **Make your changes** with tests
6. **Submit a pull request**

### CI/CD Pipeline

Every push and pull request automatically runs:
- ✅ Black (code formatting)
- ✅ Flake8 (linting)
- ✅ MyPy (type checking)
- ✅ Pytest (unit tests on Python 3.10, 3.11, 3.12)
- ✅ Security scans (CodeQL, Bandit)
- ✅ Docker builds

**View CI status**: [Actions tab](https://github.com/Erics38/restaurant-ai-chatbot/actions)

### Before Submitting

Run checks locally to catch issues early:

```bash
# All-in-one verification script
./scripts/verify-ci-locally.sh

# Or run individually
black app/ tests/ --line-length=120
flake8 app/ tests/ --max-line-length=120 --extend-ignore=E203,W503
mypy app/ --ignore-missing-imports
pytest tests/ -v
```

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) and [CICD_SETUP.md](CICD_SETUP.md) for detailed documentation.

---

## Support

- **Issues:** https://github.com/Erics38/restaurant-ai-chatbot/issues
- **API Docs:** http://localhost:8000/api/docs (when running locally)

---

Built with FastAPI and Python.
