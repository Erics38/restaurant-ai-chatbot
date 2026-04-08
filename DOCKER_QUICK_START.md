# Docker Quick Start Guide

Super simple way to run Restaurant AI with Docker! Choose your mode:

## Option 1: Template Mode (Easiest - No AI Model)

**What you get**: Instant responses, perfect for testing
**Time to start**: 1 minute
**Requirements**: Just Docker

### Windows:
```bash
./start-template.bat
```

### macOS/Linux:
```bash
chmod +x start-template.sh
./start-template.sh
```

### Manual command:
```bash
docker-compose up --build -d
```

**Access**:
- Chat: http://localhost:8000/static/restaurant_chat.html
- API: http://localhost:8000/api/docs

---

## Option 2: AI Mode (Smart - With Llama-3-8B Model)

**What you get**: Natural language AI responses
**Time to start**: 2-3 minutes (first time)
**Requirements**: Docker + 4.92GB model file

### Step 1: Download Model (one-time, ~2 minutes)

```bash
# Create models directory
mkdir -p models

# Download Llama-3-8B model (4.92GB)
curl -L -o models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf \
  https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf
```

### Step 2: Start with AI

**Windows**:
```bash
./start-ai.bat
```

**macOS/Linux**:
```bash
chmod +x start-ai.sh
./start-ai.sh
```

**Manual command**:
```bash
USE_LOCAL_AI=true docker-compose --profile ai up --build -d
```

**Access**:
- Chat: http://localhost:8000/static/restaurant_chat.html
- API: http://localhost:8000/api/docs
- AI Server: http://localhost:8080/health

---

## Useful Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Just the app
docker-compose logs -f app

# Just the AI server
docker-compose logs -f llama-server
```

### Stop Everything
```bash
# Template mode
docker-compose down

# AI mode
docker-compose --profile ai down
```

### Restart
```bash
# Template mode
docker-compose restart

# AI mode
docker-compose --profile ai restart
```

### Check Status
```bash
docker-compose ps
```

### Rebuild After Code Changes
```bash
# Template mode
docker-compose up --build -d

# AI mode
docker-compose --profile ai up --build -d
```

---

## Troubleshooting

### Port Already in Use
```bash
# Stop all containers first
docker-compose --profile ai down

# Check what's using the port
# Windows:
netstat -ano | findstr :8000
# macOS/Linux:
lsof -ti:8000
```

### AI Not Responding
```bash
# Check if llama-server is running
docker-compose ps

# Check llama-server logs
docker-compose logs llama-server

# Make sure model file exists
ls -lh models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf
```

### Slow First Response
- Normal! The AI model takes 30-60 seconds to load on first start
- Check logs: `docker-compose logs -f llama-server`
- Look for: "server is listening on http://0.0.0.0:8080"

### Out of Memory
```bash
# AI mode needs ~4GB RAM
# Check Docker memory settings:
# Docker Desktop → Settings → Resources → Memory → Set to 6GB+
```

### Container Won't Start
```bash
# Remove old containers and volumes
docker-compose --profile ai down -v

# Rebuild from scratch
docker-compose --profile ai up --build -d
```

---

## How It Works

### Template Mode
```
User → restaurant-ai container → Fast template responses
```

### AI Mode
```
User → restaurant-ai container → llama-server container → Llama-3-8B model → Smart AI responses
```

Both containers run in the same Docker network and can talk to each other.

---

## What Gets Created

When you run Docker Compose, it creates:

```
restaurant-ai/
├── data/
│   └── orders.db          ← Created automatically
├── logs/
│   └── app.log           ← Created automatically
└── models/
    └── Meta-Llama-3-8B-Instruct.Q4_K_M.gguf ← You download this once
```

The containers mount these directories, so data persists even when you stop/restart.

---

## Performance Comparison

| Mode | Response Time | Memory | Setup Time |
|------|--------------|--------|------------|
| Template | <10ms | 200MB | 1 minute |
| AI | 2-10 seconds | 4GB | 3 minutes |

---

## Deployment to Production

### For Template Mode:
```bash
# Just works anywhere with Docker!
docker-compose up -d
```

### For AI Mode:
```bash
# Requires server with 4GB+ RAM
docker-compose --profile ai up -d
```

**Cloud Providers**:
- **DigitalOcean**: $24/month (4GB droplet)
- **AWS EC2**: t3.medium ($30/month)
- **Google Cloud**: e2-standard-2 ($50/month)
- **Hetzner**: CPX21 (€8.90/month - cheapest!)

---

## Next Steps

Once running:
1. Open http://localhost:8000/static/restaurant_chat.html
2. Try: "hey what burgers do you have?"
3. Try VIP mode: "hi, i'm on yelp"
4. Check API docs: http://localhost:8000/api/docs

Want to customize?
- Edit menu: `app/menu_data.py`
- Change personality: `app/tobi_ai.py`
- Add endpoints: `app/main.py`

---

You can now run Restaurant AI with Docker.
