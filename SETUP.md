# Setup Guide — Restaurant AI Chatbot

Complete setup instructions for running the Restaurant AI chatbot locally.

## Prerequisites

| Requirement | Minimum Version | Check |
|---|---|---|
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.0+ | `docker compose version` |
| Disk space | 3 GB free | For model + containers |
| RAM | 4 GB available | For AI model serving |

## Step 1: Clone the Repository

```bash
git clone https://github.com/Erics38/restaurant-ai-chatbot.git
cd restaurant-ai-chatbot
```

## Step 2: Configure Environment

```bash
cp .env.example .env
```

Open `.env` and review these fields:

| Variable | Default | Notes |
|---|---|---|
| `PORT` | `8000` | Change if 8000 is in use |
| `ENVIRONMENT` | `development` | Use `production` for deployments |
| `USE_LOCAL_AI` | `true` | Set `false` to skip AI, use instant templates |
| `MAGIC_PASSWORD` | `i'm on yelp` | Triggers VIP mode in chat |
| `SECRET_KEY` | (empty) | Generate with: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |

## Step 3: Download the AI Model (Required for AI mode)

This is a one-time download of ~1.7 GB.

```bash
mkdir -p models
curl -L -o models/phi-2.Q4_K_M.gguf \
  https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf
```

To verify the download:
```bash
ls -lh models/phi-2.Q4_K_M.gguf
# Expected: file is approximately 1.7 GB
```

## Step 4: Start the Application

**With AI (full mode, 2–10s responses):**
```bash
# macOS/Linux
chmod +x start.sh && ./start.sh

# Windows
start.bat

# Or directly:
docker-compose up --build -d
```

**Without AI (instant template responses, for development/demo):**
```bash
USE_LOCAL_AI=false docker-compose up -d
```

## Step 5: Verify It's Running

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "environment": "development"}
```

Open the chat interface: http://localhost:8000/static/restaurant_chat.html

## Troubleshooting

**Port 8000 already in use:**
```bash
# Edit .env and change PORT=8001, then restart
docker-compose down && docker-compose up -d
```

**Model not found error:**
```bash
# Verify model file exists and path matches docker-compose.yml
ls -la models/
```

**Container fails to start:**
```bash
docker-compose logs app
docker-compose logs llama-server
```

**Slow AI responses (>30s):**
This is expected on machines without GPU support. Use template mode for demos:
```bash
USE_LOCAL_AI=false docker-compose up -d
```

## Stopping the Application

```bash
docker-compose down
```

To remove all data (orders database):
```bash
docker-compose down -v
```

## API Documentation

Once running, interactive API docs are available at:
- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc
