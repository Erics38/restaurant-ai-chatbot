# Docker Fixes Applied - 2026-04-06

## Summary

Successfully diagnosed and fixed Docker container connection issues. All containers are now running properly with AI functionality enabled.

---

## Issues Fixed

### 1. ✅ USE_LOCAL_AI Disabled by Default

**Problem:** AI was disabled by default, causing app to use template responses instead of LLM

**Fix Applied:** [docker-compose.yml:36](./docker-compose.yml#L36)
```yaml
# Before:
- USE_LOCAL_AI=${USE_LOCAL_AI:-false}

# After:
- USE_LOCAL_AI=${USE_LOCAL_AI:-true}
```

### 2. ✅ No Startup Dependency

**Problem:** App container started before llama-server was ready

**Fix Applied:** [docker-compose.yml:39-41](./docker-compose.yml#L39-L41)
```yaml
# Added:
depends_on:
  llama-server:
    condition: service_healthy
```

**Result:** App now waits for llama-server to pass health checks before starting

### 3. ✅ Insufficient Timeout

**Problem:** 30-second timeout was too short for CPU-based LLM inference

**Fix Applied:** [app/tobi_ai.py:210,286](./app/tobi_ai.py)
```python
# Before:
async with httpx.AsyncClient(timeout=30.0) as client:

# After:
async with httpx.AsyncClient(timeout=60.0) as client:
```

**Result:** 60-second timeout accommodates slower CPU inference

### 4. ✅ Poor Error Logging

**Problem:** Generic exception handling hid actual errors

**Fix Applied:** [app/tobi_ai.py:234-246](./app/tobi_ai.py)
```python
# Before:
except Exception as e:
    logger.error(f"Error calling llama-server: {e}")

# After:
except httpx.TimeoutException as e:
    logger.error(f"Timeout calling llama-server (60s exceeded): {e}", exc_info=True)
except httpx.ConnectError as e:
    logger.error(f"Connection error to llama-server: {e}", exc_info=True)
except Exception as e:
    logger.error(f"Unexpected error calling llama-server: {e}", exc_info=True)
```

**Result:** Full tracebacks now logged for easier debugging

---

## Test Results

### Container Status
```
✓ restaurant-ai-llama: Running (healthy)
✓ restaurant-ai: Running (healthy)
✓ Same network: restaurant-ai-chatbot_restaurant-network
✓ DNS resolution: llama-server resolves correctly
✓ HTTP connectivity: App can reach llama-server
```

### Environment Variables
```
✓ USE_LOCAL_AI=true
✓ LLAMA_SERVER_URL=http://llama-server:8080
```

### Connectivity Tests
```
✓ App health endpoint: http://localhost:8000/health
✓ Llama models endpoint: http://localhost:8080/v1/models
✓ Cross-container communication: Working
✓ AI chat completion: Working (52s response time)
```

### Performance Notes
- **First inference (cold start):** ~52-60 seconds
- **Reason:** CPU-only inference with 8B parameter model
- **Recommendation:** Consider GPU acceleration or smaller model for production

---

## Files Modified

1. **docker-compose.yml**
   - Enabled AI by default
   - Added startup dependency

2. **app/tobi_ai.py**
   - Increased timeout to 60s
   - Improved error handling with specific exception types
   - Added full traceback logging

---

## Testing Infrastructure Created

### Test Files
```
tests/
├── test_docker_health.py       # Comprehensive pytest suite (79 tests)
├── docker_diagnostic.py        # Standalone diagnostic script
├── docker_diagnostic.sh        # Bash version (Linux/Mac)
├── docker_diagnostic.ps1       # PowerShell version (Windows)
├── requirements-test.txt       # Test dependencies
└── README.md                   # Test documentation
```

### Documentation
```
├── DOCKER_TESTING_GUIDE.md     # Complete reference guide
└── FIXES_APPLIED.md            # This file
```

---

## Running the Tests

### Quick Diagnostic (No dependencies needed)
```bash
cd tests
python docker_diagnostic.py
```

### Full Test Suite
```bash
cd tests
pip install -r requirements-test.txt
pytest test_docker_health.py -v -s
```

### Specific Tests
```bash
# Test container health
pytest test_docker_health.py::TestDockerContainerHealth -v

# Test network
pytest test_docker_health.py::TestDockerNetwork -v

# Test connectivity
pytest test_docker_health.py::TestLlamaServerConnectivity -v

# Test environment
pytest test_docker_health.py::TestEnvironmentConfiguration -v
```

---

## Common Issues & Solutions

### Issue: Timeout Still Occurring

**Symptom:** Even with 60s timeout, requests time out

**Cause:** CPU inference is very slow (50-60s per request)

**Solutions:**

1. **Increase timeout further** (not recommended for production):
   ```python
   async with httpx.AsyncClient(timeout=120.0) as client:
   ```

2. **Use smaller model** (recommended):
   ```yaml
   # In docker-compose.yml, use Q4_K_S instead of Q4_K_M
   --model /models/Meta-Llama-3-8B-Instruct.Q4_K_S.gguf
   ```

3. **Reduce context length**:
   ```yaml
   --n_ctx 2048  # Reduced from 4096
   ```

4. **Add GPU support** (best option):
   ```yaml
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: 1
             capabilities: [gpu]
   ```

### Issue: Containers Unhealthy

**Check:**
```bash
docker inspect -f '{{json .State.Health}}' restaurant-ai | python -m json.tool
docker logs --tail 50 restaurant-ai
```

**Common causes:**
- Still within start_period (15 min for llama-server)
- Health check endpoint not responding
- Container port not accessible

### Issue: Connection Refused

**Check network:**
```bash
docker network inspect restaurant-ai-chatbot_restaurant-network
docker exec restaurant-ai ping llama-server
```

**Fix:**
```bash
# Recreate containers to ensure same network
docker-compose down
docker-compose up -d
```

---

## Performance Optimization Tips

### 1. Use GPU (Recommended)
```yaml
# Add to llama-server in docker-compose.yml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### 2. Use Smaller Quantization
```yaml
# Q4_K_S is smaller and faster than Q4_K_M
--model /models/Meta-Llama-3-8B-Instruct.Q4_K_S.gguf
```

### 3. Reduce Context Window
```yaml
--n_ctx 2048  # Instead of 4096
```

### 4. Limit Concurrent Requests
```python
# Add semaphore in tobi_ai.py
import asyncio

# Global semaphore to limit concurrent requests
_llama_semaphore = asyncio.Semaphore(1)

async def get_ai_response(prompt: str) -> str:
    async with _llama_semaphore:
        # existing code...
```

### 5. Add Request Caching
```python
# Cache common queries
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_response(prompt: str) -> str:
    # Check if we've seen this exact prompt before
    pass
```

---

## Monitoring Commands

### Real-time Logs
```bash
# Both containers
docker-compose logs -f

# Just app
docker logs -f restaurant-ai

# Just llama
docker logs -f restaurant-ai-llama
```

### Resource Usage
```bash
# Continuous monitoring
docker stats

# Single snapshot
docker stats --no-stream restaurant-ai restaurant-ai-llama
```

### Health Status
```bash
# Check health
docker ps

# Detailed health info
docker inspect -f '{{.State.Health.Status}}' restaurant-ai
docker inspect -f '{{json .State.Health}}' restaurant-ai | python -m json.tool
```

---

## Next Steps

### Short Term
1. ✅ Containers running with AI enabled
2. ✅ Proper error logging in place
3. ✅ Health checks working
4. ✅ Test infrastructure created

### Medium Term (Optional)
1. Consider GPU acceleration for faster inference
2. Implement request caching for common queries
3. Add monitoring/alerting for container health
4. Optimize model size vs quality tradeoff

### Long Term (Optional)
1. Implement load balancing if scaling needed
2. Add response streaming for better UX
3. Consider using managed LLM service for production
4. Implement A/B testing between models

---

## Reference Links

- Main Guide: [DOCKER_TESTING_GUIDE.md](./DOCKER_TESTING_GUIDE.md)
- Test README: [tests/README.md](./tests/README.md)
- Docker Compose: [docker-compose.yml](./docker-compose.yml)
- AI Implementation: [app/tobi_ai.py](./app/tobi_ai.py)

---

## Summary

All identified issues have been resolved:

✅ AI functionality enabled by default
✅ Proper startup ordering (llama-server → app)
✅ Adequate timeout for CPU inference
✅ Comprehensive error logging
✅ Test infrastructure for ongoing monitoring
✅ Complete documentation

The system is now fully functional with AI-powered responses. Performance is limited by CPU-only inference (~50-60s per request), but this is expected without GPU acceleration.

**Status:** Ready for development/testing. Consider GPU or smaller model for production use.

---

**Applied by:** Claude Code
**Date:** 2026-04-06
**Version:** 1.0
