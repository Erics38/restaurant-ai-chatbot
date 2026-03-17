# 🍔 Restaurant AI - The Common House

An AI-powered restaurant ordering system featuring **Tobi**, a surfer-style chatbot assistant with menu awareness.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.118+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![CI Status](https://github.com/Erics38/Tobi-the-local-server-serving-server/actions/workflows/ci.yml/badge.svg)
![Docker Build](https://github.com/Erics38/Tobi-the-local-server-serving-server/actions/workflows/docker.yml/badge.svg)

---

## ✨ Features

- 🤖 **Menu-Aware AI Chatbot** - Tobi understands food categories, ingredients, and can recommend items
- 🧠 **AI-Powered by Default** - Uses local Phi-2 model for natural language understanding (2-10s)
- ⚡ **Template Fallback** - Instant responses (<10ms) if AI unavailable or for development
- 🍽️ **Full Menu System** - Starters, Mains, Desserts, and Drinks
- 📋 **Order Management** - Create and track orders with presidential birth year order numbers
- 🎯 **Magic Password** - VIP treatment for special customers ("i'm on yelp")
- 💾 **SQLite Database** - Persistent order storage
- 🔒 **Production Ready** - Proper logging, health checks, and error handling
- 🐳 **Docker Support** - One-command deployment
- 🔧 **Environment-Based Config** - Easy configuration via `.env` files
- 💰 **Zero API Costs** - Run AI models locally with no external dependencies

---

## 🏗️ Infrastructure Architecture

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
             │ SQLite                        │ HTTP POST
             │                               │
             ▼                               ▼
┌──────────────────────┐    ┌────────────────────────────────────┐
│   SQLite Database    │    │   llama-server (Optional)          │
│   (data/orders.db)   │    │   Port 8080                        │
├──────────────────────┤    ├────────────────────────────────────┤
│ • Orders             │    │ • Phi-2 Model (1.7GB)              │
│ • Presidential       │    │ • Natural Language Processing      │
│   Order Numbers      │    │ • Context: 4096 tokens             │
│ • Session Tracking   │    │ • Response time: 2-10s             │
└──────────────────────┘    └────────────────────────────────────┘

Data Flow:
─────────
1. User sends message in chat → FastAPI /chat endpoint
2. If USE_LOCAL_AI=true:
   → FastAPI → llama-server (AI generates response)
3. If USE_LOCAL_AI=false or AI unavailable:
   → FastAPI uses template responses (instant)
4. User creates order → FastAPI → SQLite (stores order)
5. FastAPI returns order confirmation with presidential year number

Docker Compose Setup:
────────────────────
┌─────────────────────────────────────────────────────────────────┐
│ Docker Compose (docker-compose.yml)                            │
├─────────────────────────────────────────────────────────────────┤
│ ┌───────────────────┐         ┌──────────────────────┐         │
│ │  app container    │◄────────┤ llama-server         │         │
│ │  (restaurant-ai)  │  HTTP   │ container            │         │
│ │  Port: 8000       │         │ Port: 8080           │         │
│ └─────────┬─────────┘         └──────────┬───────────┘         │
│           │                               │                     │
│           ▼                               ▼                     │
│   ┌──────────────┐              ┌─────────────────┐            │
│   │ Volume:      │              │ Volume:         │            │
│   │ ./data       │              │ ./models        │            │
│   │ (orders.db)  │              │ (phi-2.gguf)    │            │
│   └──────────────┘              └─────────────────┘            │
└─────────────────────────────────────────────────────────────────┘

Technology Stack:
────────────────
Backend:  FastAPI (Python 3.11+)
AI:       llama.cpp + Phi-2 (GGUF format)
Database: SQLite (development) / PostgreSQL (production ready)
Frontend: HTML/JavaScript (static files)
Deploy:   Docker + Docker Compose
```

---

## 🚀 Quick Start

**Prerequisites**: Docker + 1.7GB Phi-2 model

### Step 1: Download Model (one-time)

```bash
mkdir -p models
curl -L -o models/phi-2.Q4_K_M.gguf \
  https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf
```

### Step 2: Start with Docker (AI-powered)

```bash
# Windows:
start.bat

# macOS/Linux:
chmod +x start.sh && ./start.sh

# Or manually:
docker-compose up --build -d
```

**Access**: http://localhost:8000/static/restaurant_chat.html

### Optional: Template Mode (Fast, No AI)

```bash
USE_LOCAL_AI=false docker-compose up -d
```

---

## 📁 Project Structure

```
restaurant-ai/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application & endpoints
│   ├── config.py        # Environment-based configuration
│   ├── models.py        # Pydantic models for validation
│   ├── database.py      # SQLite database operations
│   ├── tobi_ai.py       # AI chatbot logic (menu-aware)
│   └── menu_data.py     # Restaurant menu data
├── static/
│   └── restaurant_chat.html  # Web interface
├── data/                # Database files (git-ignored)
├── logs/                # Application logs (git-ignored)
├── models/              # AI model files (git-ignored)
├── tests/               # Unit tests
├── .env.example         # Example environment variables
├── .gitignore
├── requirements.txt     # Python dependencies
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🔧 Configuration

All configuration is managed through environment variables. Copy `.env.example` to `.env` and customize:

```bash
# Server
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development  # development, staging, production

# Database
DATABASE_URL=sqlite:///./data/orders.db

# Restaurant
RESTAURANT_NAME=The Common House

# Features
ENABLE_MAGIC_PASSWORD=True
MAGIC_PASSWORD=i'm on yelp

# Security
SECRET_KEY=your-secret-key-here  # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"

# Logging
LOG_LEVEL=INFO
```

---

## 📡 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root endpoint with basic info |
| `GET` | `/health` | Health check for monitoring |
| `GET` | `/menu` | Get full restaurant menu |
| `POST` | `/chat` | Chat with Tobi AI |
| `POST` | `/order` | Create a new order |
| `GET` | `/order/{order_number}` | Get order details |

### Interactive API Documentation

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

---

## 💬 Chat Examples

```bash
# Ask about menu items
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What burgers do you have?"}'

# Response: "Oh dude, the House Smash Burger is awesome! It's Double patty, cheddar, caramelized onion - totally worth the $16.00. Want me to add it to your order?"

# Ask for recommendations
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What do you recommend?"}'

# VIP treatment
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi, I'\''m on yelp"}'
```

---

## 📦 Creating an Order

```bash
curl -X POST http://localhost:8000/order \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"name": "House Smash Burger", "price": 16.00, "quantity": 2},
      {"name": "Truffle Fries", "price": 12.00, "quantity": 1}
    ]
  }'

# Response:
# {
#   "success": true,
#   "order_number": 1732,  # Presidential birth year!
#   "total": 44.00,
#   "message": "Order #1732 confirmed! Your food will be ready shortly."
# }
```

---

## 🧪 Testing

```bash
# Run tests (when implemented)
pytest

# Check code style
black app/
flake8 app/

# Type checking
mypy app/
```

---

## 🐳 Docker Commands

```bash
# Build and start
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop
docker-compose down

# Rebuild after code changes
docker-compose up --build
```

---

## 🔮 Future Enhancements

### Phase 2: Real AI Integration

Uncomment the `llama-server` section in `docker-compose.yml` to use actual LLM:

```yaml
llama-server:
  image: ghcr.io/ggerganov/llama.cpp:server
  volumes:
    - ./models:/models:ro
  command: -m /models/phi-2.Q4_K_M.gguf --host 0.0.0.0 --port 8080
```

Then update `.env`:
```bash
LLAMA_SERVER_URL=http://llama-server:8080/completion
```

### Phase 3: Database Upgrade

Switch to PostgreSQL for production:

```bash
# In .env
DATABASE_URL=postgresql://user:password@db:5432/restaurant
```

Add PostgreSQL service to `docker-compose.yml`.

---

## 🛠️ Development

### Hot Reload

The application supports hot reload in development mode:

```bash
# Automatic reload on code changes
python -m uvicorn app.main:app --reload

# Or with Docker (volume mounted in docker-compose.yml)
docker-compose up
```

### Adding New Menu Items

Edit `app/menu_data.py`:

```python
MENU_DATA = {
    "starters": [
        {"name": "New Item", "description": "Delicious!", "price": 15.00},
        # ...
    ]
}
```

---

## 📝 License

MIT License - feel free to use this project for your own restaurant!

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 🙋‍♂️ Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/restaurant-ai/issues)
- **Documentation**: This README and inline code comments
- **API Docs**: http://localhost:8000/api/docs

---

## 🎯 Tobi's Personality

Tobi is a chill surfer dude who loves talking about food! He uses phrases like:
- "Dude", "Bro", "Yo"
- "Rad", "Sick", "Gnarly", "Killer", "Epic"
- "Stoked", "Totally", "For sure"

Try chatting with him at: http://localhost:8000/static/restaurant_chat.html

---

## 📚 Documentation

- **[SETUP.md](SETUP.md)** - Complete setup guide for new users
- **[README_AI_INTEGRATION.md](../README_AI_INTEGRATION.md)** - Deep dive into AI features
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Upgrading from old version
- **API Docs** - http://localhost:8000/api/docs (when running)

---

**Built with ❤️ using FastAPI, Python, and a touch of surfer vibes 🏄‍♂️**
