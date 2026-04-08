# Quick Reference Card - Docker Troubleshooting

## 🚀 Quick Start

```bash
# Start everything
docker-compose up -d

# Check status
docker ps

# Follow logs
docker-compose logs -f
```

## 🔍 Quick Diagnostics

```bash
# Run diagnostic script
cd tests && python docker_diagnostic.py

# Or manually check:
docker ps                                           # Are containers running?
docker logs --tail 20 restaurant-ai                 # Any errors in app?
docker logs --tail 20 restaurant-ai-llama           # Any errors in llama?
docker exec restaurant-ai printenv USE_LOCAL_AI     # Is AI enabled?
```

## ✅ Health Checks

```bash
# Quick health check
docker inspect -f '{{.State.Health.Status}}' restaurant-ai
docker inspect -f '{{.State.Health.Status}}' restaurant-ai-llama

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8080/v1/models

# Test connectivity from app to llama
docker exec restaurant-ai python -c "import urllib.request; print(urllib.request.urlopen('http://llama-server:8080/v1/models', timeout=5).read().decode())"
```

## 🐛 Common Problems

### Problem: Containers won't start
```bash
# Full restart
docker-compose down
docker-compose up -d
```

### Problem: AI not working (using templates)
```bash
# Check if AI is enabled
docker exec restaurant-ai printenv USE_LOCAL_AI
# Should output: true

# If not, edit docker-compose.yml line 36 or create .env:
echo "USE_LOCAL_AI=true" > .env
docker-compose restart app
```

### Problem: Connection timeout
```bash
# Check if llama-server is healthy
docker ps | grep llama
# Should show "healthy" not "unhealthy"

# Check logs for model loading
docker logs restaurant-ai-llama | grep "startup complete"

# Test direct connection
curl http://localhost:8080/v1/models
```

### Problem: Containers unhealthy
```bash
# Wait for startup (llama needs ~15 min first time)
# Or check health logs:
docker inspect -f '{{json .State.Health}}' restaurant-ai | python -m json.tool
docker inspect -f '{{json .State.Health}}' restaurant-ai-llama | python -m json.tool
```

### Problem: Out of memory
```bash
# Check memory usage
docker stats --no-stream

# Increase limits in docker-compose.yml:
# llama-server -> deploy -> resources -> limits -> memory: 12G
```

## 🔧 Quick Fixes

```bash
# Restart specific service
docker-compose restart app
docker-compose restart llama-server

# View logs
docker-compose logs -f app
docker-compose logs -f llama-server

# Rebuild after code changes
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Clean restart
docker-compose down -v
docker system prune -f
docker-compose up -d
```

## 📊 Monitoring

```bash
# Watch logs continuously
docker-compose logs -f

# Monitor resources
docker stats

# Check network
docker network inspect restaurant-ai-chatbot_restaurant-network

# List containers
docker ps -a
```

## 🧪 Testing

```bash
# Quick diagnostic
cd tests && python docker_diagnostic.py

# Full test suite
cd tests && pytest test_docker_health.py -v

# Specific tests
pytest test_docker_health.py::TestDockerContainerHealth -v
pytest test_docker_health.py::TestLlamaServerConnectivity -v
pytest test_docker_health.py::TestEnvironmentConfiguration -v
```

## 📝 Important Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Container configuration |
| `app/tobi_ai.py` | AI integration code |
| `DOCKER_TESTING_GUIDE.md` | Complete troubleshooting guide |
| `FIXES_APPLIED.md` | What was fixed and why |
| `tests/docker_diagnostic.py` | Quick diagnostic script |
| `tests/test_docker_health.py` | Full test suite |

## 🎯 Key Settings

| Setting | Location | Value |
|---------|----------|-------|
| AI Enabled | docker-compose.yml:36 | `USE_LOCAL_AI:-true` |
| Timeout | app/tobi_ai.py:210,286 | `timeout=60.0` |
| Startup Dependency | docker-compose.yml:39-41 | `depends_on: llama-server` |
| Health Check Interval | docker-compose.yml:41,83 | `interval: 30s` |
| Startup Grace Period | docker-compose.yml:86 | `start_period: 900s` |

## ⚡ Performance Notes

- **CPU Inference:** ~50-60 seconds per request
- **First request:** May be slower (model loading)
- **Timeout:** Set to 60s to accommodate CPU speed
- **Improvement:** Add GPU for <1s inference

## 🆘 Emergency Commands

```bash
# Containers crashed/won't start
docker-compose down && docker-compose up -d

# Everything is broken
docker-compose down -v
docker system prune -af
docker-compose up -d --build

# Check what's using ports
netstat -ano | findstr "8000"
netstat -ano | findstr "8080"

# View full container details
docker inspect restaurant-ai
docker inspect restaurant-ai-llama
```

## 📞 When to Use Each Guide

| Use Case | Guide |
|----------|-------|
| Quick problem? | This file |
| Detailed troubleshooting? | `DOCKER_TESTING_GUIDE.md` |
| What was fixed? | `FIXES_APPLIED.md` |
| Running tests? | `tests/README.md` |
| Understanding code? | Code comments in `app/` |

## ✨ Success Indicators

✅ `docker ps` shows both containers as "healthy"
✅ `curl http://localhost:8000/health` returns `{"status":"healthy"}`
✅ `curl http://localhost:8080/v1/models` returns model list
✅ Chat requests get AI responses (not just templates)
✅ Logs show "AI response" not "Falling back to template"

---

**Quick Links:**
- [Full Guide](./DOCKER_TESTING_GUIDE.md)
- [Fixes Applied](./FIXES_APPLIED.md)
- [Test README](./tests/README.md)
