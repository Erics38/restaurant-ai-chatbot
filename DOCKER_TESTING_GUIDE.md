# Docker Testing & Troubleshooting Guide

**Complete reference for diagnosing and fixing Docker container issues**

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Issues Found & Solutions](#issues-found--solutions)
3. [Test Suite Overview](#test-suite-overview)
4. [Running Tests](#running-tests)
5. [Common Issues & Fixes](#common-issues--fixes)
6. [Docker Health Tests](#docker-health-tests)
7. [Manual Testing Commands](#manual-testing-commands)
8. [Monitoring & Debugging](#monitoring--debugging)
9. [Preventive Measures](#preventive-measures)
10. [Reference Scripts](#reference-scripts)

---

## Quick Diagnostics

### Windows PowerShell Quick Check

```powershell
# Check container status
docker ps -a | Select-String "restaurant"

# Check health status
docker inspect -f "{{.State.Health.Status}}" restaurant-ai
docker inspect -f "{{.State.Health.Status}}" restaurant-ai-llama

# Check environment variables
docker exec restaurant-ai printenv USE_LOCAL_AI
docker exec restaurant-ai printenv LLAMA_SERVER_URL

# Test connectivity
docker exec restaurant-ai python -c "import urllib.request; print(urllib.request.urlopen('http://llama-server:8080/v1/models', timeout=5).read().decode())"

# Check logs
docker logs --tail 20 restaurant-ai
docker logs --tail 20 restaurant-ai-llama
```

### Linux/Mac Quick Check

```bash
# Check container status
docker ps -a | grep restaurant

# Check health status
docker inspect -f '{{.State.Health.Status}}' restaurant-ai
docker inspect -f '{{.State.Health.Status}}' restaurant-ai-llama

# Check environment variables
docker exec restaurant-ai printenv USE_LOCAL_AI
docker exec restaurant-ai printenv LLAMA_SERVER_URL

# Test connectivity
docker exec restaurant-ai python -c "import urllib.request; print(urllib.request.urlopen('http://llama-server:8080/v1/models', timeout=5).read().decode())"

# Check logs
docker logs --tail 20 restaurant-ai
docker logs --tail 20 restaurant-ai-llama
```

---

## Issues Found & Solutions

### Issue 1: USE_LOCAL_AI is False (AI Disabled)

**Symptom:**
- App returns template responses instead of AI-generated responses
- Logs show "Falling back to template responses"
- No actual AI processing happening

**Root Cause:**
```yaml
# In docker-compose.yml line 36
- USE_LOCAL_AI=${USE_LOCAL_AI:-false}  # ← Defaults to false
```

**Solution:**

Option 1 - Edit docker-compose.yml:
```yaml
# Change line 36 to:
- USE_LOCAL_AI=${USE_LOCAL_AI:-true}  # ← Default to true
```

Option 2 - Create .env file:
```bash
# In project root, create/edit .env
echo "USE_LOCAL_AI=true" >> .env
```

Option 3 - Set environment variable before starting:
```bash
export USE_LOCAL_AI=true  # Linux/Mac
# or
$env:USE_LOCAL_AI="true"  # PowerShell

docker-compose up -d
```

After changing, restart:
```bash
docker-compose restart app
```

### Issue 2: Containers Showing as Unhealthy

**Symptom:**
- `docker ps` shows "(unhealthy)" status
- Services may work but marked unhealthy

**Check Health Details:**
```bash
# See health check logs
docker inspect restaurant-ai --format='{{json .State.Health}}' | python -m json.tool
docker inspect restaurant-ai-llama --format='{{json .State.Health}}' | python -m json.tool
```

**Common Causes:**

1. **Still starting up** - llama-server has 900s (15 min) start period
   ```bash
   # Check uptime
   docker inspect -f '{{.State.StartedAt}}' restaurant-ai-llama
   ```

2. **Wrong health check endpoint** - Check if endpoints exist
   ```bash
   # Test app health endpoint
   curl http://localhost:8000/health

   # Test llama health endpoint
   curl http://localhost:8080/v1/models
   ```

3. **Port not accessible inside container**
   ```bash
   # Test from inside container
   docker exec restaurant-ai curl http://localhost:8000/health
   docker exec restaurant-ai-llama curl http://localhost:8080/v1/models
   ```

**Solution:**
```bash
# Wait for startup period to complete (15 min for llama)
# Or check logs for actual errors
docker logs restaurant-ai-llama | grep -i error

# Restart if needed
docker-compose restart
```

### Issue 3: Connection Timeout Between Containers

**Symptom:**
- "Error calling llama-server" in app logs
- Connection timeout errors
- DNS resolution failures

**Diagnostic Steps:**

1. **Check containers are on same network:**
   ```bash
   docker inspect restaurant-ai -f '{{range $key, $value := .NetworkSettings.Networks}}{{$key}}{{end}}'
   docker inspect restaurant-ai-llama -f '{{range $key, $value := .NetworkSettings.Networks}}{{$key}}{{end}}'
   ```

2. **Test DNS resolution:**
   ```bash
   docker exec restaurant-ai python -c "import socket; print(socket.gethostbyname('llama-server'))"
   ```

3. **Test socket connectivity:**
   ```bash
   docker exec restaurant-ai python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('llama-server', 8080)); print('Connected')"
   ```

4. **Test HTTP connection:**
   ```bash
   docker exec restaurant-ai curl -v http://llama-server:8080/v1/models
   ```

**Solutions:**

If DNS fails:
```bash
# Recreate containers with docker-compose (ensures same network)
docker-compose down
docker-compose up -d
```

If llama-server not responding:
```bash
# Check if llama-server is actually listening
docker exec restaurant-ai-llama netstat -tuln | grep 8080

# Check llama-server logs
docker logs restaurant-ai-llama | tail -50
```

If llama-server still loading model:
```bash
# Wait longer, check logs for loading progress
docker logs -f restaurant-ai-llama
# Look for "Application startup complete" message
```

### Issue 4: Container Exits with Code 137

**Symptom:**
- Container stops unexpectedly
- Exit code 137 in `docker ps -a`

**Cause:**
- Exit code 137 = 128 + 9 (SIGKILL)
- Usually means Docker killed the container due to OOM (Out of Memory)

**Check Memory Usage:**
```bash
# Check current stats
docker stats --no-stream

# Check memory limits
docker inspect restaurant-ai-llama -f '{{.HostConfig.Memory}}'

# Check for OOM in logs
docker logs restaurant-ai-llama | grep -i "out of memory"
docker logs restaurant-ai-llama | grep -i "oom"
```

**Solution:**

Increase memory limits in docker-compose.yml:
```yaml
llama-server:
  deploy:
    resources:
      limits:
        memory: 12G  # Increased from 9G
        cpus: '4.0'
      reservations:
        memory: 10G  # Increased from 7G
        cpus: '2.0'
```

Or reduce model size:
```yaml
# Use a smaller quantized model
command: >
  python -m llama_cpp.server
  --model /models/Meta-Llama-3-8B-Instruct.Q4_K_S.gguf  # Smaller quantization
```

### Issue 5: Model File Not Found

**Symptom:**
- llama-server fails to start
- "No such file or directory" errors

**Check Model File:**
```bash
# Check on host
ls -lh ./models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf

# Check in container
docker exec restaurant-ai-llama ls -lh /models/

# Check volume mounts
docker inspect restaurant-ai-llama -f '{{json .Mounts}}' | python -m json.tool
```

**Solution:**

Ensure model file exists:
```bash
# Download model if missing (example with wget)
cd models
wget https://huggingface.co/.../Meta-Llama-3-8B-Instruct.Q4_K_M.gguf

# Or verify mount path in docker-compose.yml
volumes:
  - ./models:/models:ro  # Should point to correct directory
```

### Issue 6: Healthcheck Failing Due to Missing Dependencies

**Symptom:**
- Health check logs show "command not found"
- Health status stuck on "starting" or "unhealthy"

**Check Health Command:**
```bash
# See what healthcheck is running
docker inspect restaurant-ai -f '{{.Config.Healthcheck.Test}}'

# Test healthcheck manually
docker exec restaurant-ai python -c "import requests; requests.get('http://localhost:8000/health')"
```

**Solution:**

Ensure required packages in Dockerfile:
```dockerfile
# Add to Dockerfile if missing
RUN pip install requests urllib3
```

Or simplify healthcheck to use urllib instead of requests:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
```

---

## Test Suite Overview

### Files Created

```
tests/
├── test_docker_health.py      # Comprehensive pytest suite
├── docker_diagnostic.py       # Standalone Python diagnostic
├── docker_diagnostic.sh       # Bash diagnostic script
├── docker_diagnostic.ps1      # PowerShell diagnostic script
├── requirements-test.txt      # Test dependencies
└── README.md                  # Test documentation
```

### Test Categories

1. **Container Health Tests** - Status, restarts, uptime, exit codes
2. **Network Tests** - DNS, connectivity, IP addresses, network driver
3. **Connectivity Tests** - HTTP endpoints, response times, API functionality
4. **Resource Tests** - Memory, CPU, limits, usage
5. **Volume Tests** - Mounts, file accessibility
6. **Environment Tests** - Configuration, variables
7. **Log Tests** - Error patterns, OOM detection
8. **Docker Compose Tests** - Project names, service configuration

---

## Running Tests

### Prerequisites

```bash
cd tests
pip install -r requirements-test.txt
```

Dependencies:
- pytest>=7.4.0
- pytest-asyncio>=0.21.0
- httpx>=0.24.0
- docker>=6.1.0

### Run All Tests

```bash
# Verbose with output
pytest test_docker_health.py -v -s

# Quiet mode
pytest test_docker_health.py

# With detailed output
pytest test_docker_health.py -vv
```

### Run Specific Test Categories

```bash
# Container health tests only
pytest test_docker_health.py::TestDockerContainerHealth -v -s

# Network tests only
pytest test_docker_health.py::TestDockerNetwork -v -s

# Connectivity tests only
pytest test_docker_health.py::TestLlamaServerConnectivity -v -s

# Resource tests only
pytest test_docker_health.py::TestDockerResources -v -s

# Environment tests only
pytest test_docker_health.py::TestEnvironmentConfiguration -v -s
```

### Run Individual Tests

```bash
# Test container status
pytest test_docker_health.py::TestDockerContainerHealth::test_containers_running -v

# Test DNS resolution
pytest test_docker_health.py::TestDockerNetwork::test_dns_resolution_between_containers -v -s

# Test connectivity from app to llama
pytest test_docker_health.py::TestLlamaServerConnectivity::test_llama_server_from_app_container -v -s

# Test environment configuration
pytest test_docker_health.py::TestEnvironmentConfiguration::test_use_local_ai_setting -v -s
```

### Run Without pytest (Standalone Diagnostic)

```bash
# Python diagnostic
python docker_diagnostic.py

# Bash (Linux/Mac)
./docker_diagnostic.sh

# PowerShell (Windows) - Note: May need escaping fixes for complex commands
# Better to use Python version on Windows
python docker_diagnostic.py
```

---

## Docker Health Tests

### Complete Test List

#### TestDockerContainerHealth
```python
test_containers_running                  # Verify both containers exist and are running
test_containers_on_same_network          # Verify shared network
test_container_health_status             # Check health check results
test_port_mappings                       # Verify port exposure
test_container_restart_count             # Detect crash loops
test_container_uptime                    # Check how long running
test_container_exit_code                 # Check for error exits
```

#### TestDockerNetwork
```python
test_network_exists                      # Verify network creation
test_network_driver                      # Verify bridge driver
test_dns_resolution_between_containers   # Test hostname resolution
test_network_connectivity_ping           # Test socket connectivity
test_container_ip_addresses              # Display and verify IPs
```

#### TestLlamaServerConnectivity
```python
test_llama_server_from_host              # Access from host machine
test_llama_server_from_app_container     # Access from app container
test_llama_server_chat_completion        # Test AI functionality
test_llama_server_response_time          # Measure performance
```

#### TestAppConnectivity
```python
test_app_health_endpoint                 # Test /health endpoint
test_app_root_endpoint                   # Test / endpoint
test_app_chat_endpoint_with_ai_disabled  # Test chat with templates
```

#### TestDockerResources
```python
test_memory_limits                       # Check memory configuration
test_cpu_limits                          # Check CPU configuration
test_container_stats                     # Real-time resource usage
```

#### TestDockerVolumes
```python
test_volume_mounts                       # Verify mount configuration
test_model_file_exists                   # Check model accessibility
```

#### TestEnvironmentConfiguration
```python
test_use_local_ai_setting                # Check AI enabled/disabled
test_all_environment_variables           # Display all env vars
```

#### TestContainerLogs
```python
test_app_container_logs                  # Check app logs for errors
test_llama_container_logs                # Check llama logs
test_logs_for_oom_errors                 # Detect memory issues
```

#### TestDockerCompose
```python
test_compose_project_name                # Verify project name
test_compose_service_names               # Verify service names
```

---

## Manual Testing Commands

### Container Status

```bash
# List all containers
docker ps -a

# Check specific container status
docker inspect -f '{{.State.Status}}' restaurant-ai
docker inspect -f '{{.State.Status}}' restaurant-ai-llama

# Check health status
docker inspect -f '{{.State.Health.Status}}' restaurant-ai
docker inspect -f '{{.State.Health.Status}}' restaurant-ai-llama

# Check uptime
docker inspect -f '{{.State.StartedAt}}' restaurant-ai
docker inspect -f '{{.State.StartedAt}}' restaurant-ai-llama

# Check restart count
docker inspect -f '{{.RestartCount}}' restaurant-ai
docker inspect -f '{{.RestartCount}}' restaurant-ai-llama

# Check exit code
docker inspect -f '{{.State.ExitCode}}' restaurant-ai
docker inspect -f '{{.State.ExitCode}}' restaurant-ai-llama
```

### Network Testing

```bash
# List networks
docker network ls

# Inspect network
docker network inspect restaurant-ai-chatbot_restaurant-network

# Check container network
docker inspect -f '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{$value.IPAddress}}{{end}}' restaurant-ai

# Test DNS from app container
docker exec restaurant-ai nslookup llama-server
# Or using Python
docker exec restaurant-ai python -c "import socket; print(socket.gethostbyname('llama-server'))"

# Test connectivity
docker exec restaurant-ai ping -c 3 llama-server
# Or using Python socket
docker exec restaurant-ai python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('llama-server', 8080)); print('Connected')"
```

### Port Testing

```bash
# Check port mappings
docker port restaurant-ai
docker port restaurant-ai-llama

# Test from host
curl http://localhost:8000/
curl http://localhost:8080/v1/models

# Test from inside container
docker exec restaurant-ai curl http://localhost:8000/health
docker exec restaurant-ai-llama curl http://localhost:8080/v1/models

# Test cross-container
docker exec restaurant-ai curl http://llama-server:8080/v1/models
```

### Resource Monitoring

```bash
# Real-time stats
docker stats

# Single snapshot
docker stats --no-stream

# Specific containers
docker stats restaurant-ai restaurant-ai-llama

# Check memory limit
docker inspect -f '{{.HostConfig.Memory}}' restaurant-ai-llama

# Check CPU limit
docker inspect -f '{{.HostConfig.CpuQuota}} {{.HostConfig.CpuPeriod}}' restaurant-ai-llama
```

### Log Analysis

```bash
# Follow logs
docker logs -f restaurant-ai
docker logs -f restaurant-ai-llama

# Last N lines
docker logs --tail 50 restaurant-ai
docker logs --tail 50 restaurant-ai-llama

# Since timestamp
docker logs --since 10m restaurant-ai
docker logs --since "2024-01-01T00:00:00" restaurant-ai

# Search logs for errors
docker logs restaurant-ai 2>&1 | grep -i error
docker logs restaurant-ai-llama 2>&1 | grep -i error

# Check for specific patterns
docker logs restaurant-ai | grep "Error calling llama-server"
docker logs restaurant-ai | grep "Falling back to template"
docker logs restaurant-ai-llama | grep "out of memory"
```

### Environment Variables

```bash
# View all env vars
docker exec restaurant-ai env
docker exec restaurant-ai-llama env

# Check specific vars
docker exec restaurant-ai printenv USE_LOCAL_AI
docker exec restaurant-ai printenv LLAMA_SERVER_URL
docker exec restaurant-ai printenv ENVIRONMENT

# View from inspect
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' restaurant-ai
```

### Volume Inspection

```bash
# List mounts
docker inspect -f '{{json .Mounts}}' restaurant-ai | python -m json.tool
docker inspect -f '{{json .Mounts}}' restaurant-ai-llama | python -m json.tool

# Check files in mounted volumes
docker exec restaurant-ai ls -la /app/data
docker exec restaurant-ai-llama ls -la /models

# Check specific model file
docker exec restaurant-ai-llama ls -lh /models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf
```

---

## Monitoring & Debugging

### Real-Time Monitoring

```bash
# Watch logs from both containers
docker-compose logs -f

# Watch specific container
docker logs -f restaurant-ai

# Watch stats
watch docker stats --no-stream restaurant-ai restaurant-ai-llama

# Monitor health status
watch 'docker inspect -f "{{.State.Health.Status}}" restaurant-ai && docker inspect -f "{{.State.Health.Status}}" restaurant-ai-llama'
```

### Interactive Debugging

```bash
# Execute shell in container
docker exec -it restaurant-ai bash
docker exec -it restaurant-ai-llama bash

# Execute Python REPL
docker exec -it restaurant-ai python

# Test code interactively
docker exec -it restaurant-ai python -c "
from app.config import settings
print(f'USE_LOCAL_AI: {settings.use_local_ai}')
print(f'LLAMA_SERVER_URL: {settings.llama_server_url}')
"
```

### Debug Health Checks

```bash
# See health check command
docker inspect -f '{{json .Config.Healthcheck}}' restaurant-ai | python -m json.tool

# See health check history
docker inspect -f '{{json .State.Health}}' restaurant-ai | python -m json.tool

# Run health check manually
docker exec restaurant-ai python -c "import requests; print(requests.get('http://localhost:8000/health').json())"
docker exec restaurant-ai-llama python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/v1/models').read().decode())"
```

### Network Debugging

```bash
# Inspect network details
docker network inspect restaurant-ai-chatbot_restaurant-network | python -m json.tool

# Check which containers are on network
docker network inspect restaurant-ai-chatbot_restaurant-network -f '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\n"}}{{end}}'

# Test connectivity between containers
docker exec restaurant-ai ping -c 3 restaurant-ai-llama
docker exec restaurant-ai traceroute restaurant-ai-llama
```

---

## Preventive Measures

### 1. Add Proper Startup Dependencies

Edit docker-compose.yml to make app wait for llama-server:

```yaml
app:
  depends_on:
    llama-server:
      condition: service_healthy  # Wait for healthy status
```

### 2. Increase Timeouts

In app/tobi_ai.py:

```python
# Increase timeout for AI requests
async with httpx.AsyncClient(timeout=60.0) as client:  # Was 30.0
```

### 3. Add Retry Logic

```python
# In tobi_ai.py
import asyncio

async def get_ai_response_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Get AI response with retry logic."""
    for attempt in range(max_retries):
        try:
            return await get_ai_response(prompt)
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed after {max_retries} attempts: {e}")
                return get_tobi_response(prompt)
            logger.warning(f"Attempt {attempt + 1} failed, retrying...")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### 4. Better Error Logging

```python
# In tobi_ai.py, improve error handling
except Exception as e:
    logger.error(f"Error calling llama-server: {e}", exc_info=True)  # Add full traceback
    logger.info("Falling back to template responses")
```

### 5. Add Startup Health Check

Create a startup script to verify llama-server is ready:

```bash
# wait-for-llama.sh
#!/bin/bash
set -e

until curl -f http://llama-server:8080/v1/models; do
  echo "Waiting for llama-server..."
  sleep 2
done

echo "Llama-server is ready!"
exec "$@"
```

Use in docker-compose.yml:

```yaml
app:
  command: ["./wait-for-llama.sh", "python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6. Monitor Resource Usage

Add resource monitoring endpoint:

```python
# In main.py
import psutil

@app.get("/metrics")
async def metrics():
    """System metrics endpoint."""
    return {
        "memory_percent": psutil.virtual_memory().percent,
        "cpu_percent": psutil.cpu_percent(interval=1),
        "disk_percent": psutil.disk_usage('/').percent,
    }
```

### 7. Add Alerting

Create a monitoring script:

```bash
# monitor.sh
#!/bin/bash

while true; do
    # Check if containers are healthy
    APP_HEALTH=$(docker inspect -f '{{.State.Health.Status}}' restaurant-ai)
    LLAMA_HEALTH=$(docker inspect -f '{{.State.Health.Status}}' restaurant-ai-llama)

    if [ "$APP_HEALTH" != "healthy" ] || [ "$LLAMA_HEALTH" != "healthy" ]; then
        echo "ALERT: Containers unhealthy at $(date)"
        # Send alert (email, slack, etc.)
    fi

    sleep 60
done
```

---

## Reference Scripts

### Complete Diagnostic Script (Python)

Save as `quick_diagnostic.py`:

```python
#!/usr/bin/env python3
"""Quick diagnostic for Docker containers."""

import subprocess
import sys

def run_command(cmd):
    """Run command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def main():
    print("\n" + "="*60)
    print("  Restaurant AI Docker Diagnostics")
    print("="*60 + "\n")

    # Check containers
    print("Container Status:")
    code, out, err = run_command("docker ps -a | findstr restaurant" if sys.platform == "win32" else "docker ps -a | grep restaurant")
    print(out)

    # Check health
    print("\nHealth Status:")
    code, out, _ = run_command('docker inspect -f "{{.State.Health.Status}}" restaurant-ai')
    print(f"App: {out.strip()}")
    code, out, _ = run_command('docker inspect -f "{{.State.Health.Status}}" restaurant-ai-llama')
    print(f"Llama: {out.strip()}")

    # Check environment
    print("\nEnvironment:")
    code, out, _ = run_command('docker exec restaurant-ai printenv USE_LOCAL_AI')
    print(f"USE_LOCAL_AI: {out.strip()}")
    code, out, _ = run_command('docker exec restaurant-ai printenv LLAMA_SERVER_URL')
    print(f"LLAMA_SERVER_URL: {out.strip()}")

    # Test connectivity
    print("\nConnectivity Test:")
    code, out, err = run_command('docker exec restaurant-ai python -c "import urllib.request; urllib.request.urlopen(\'http://llama-server:8080/v1/models\', timeout=5).read()"')
    if code == 0:
        print("✓ Connection to llama-server: SUCCESS")
    else:
        print(f"✗ Connection to llama-server: FAILED - {err}")

    # Recent logs
    print("\nRecent App Logs:")
    code, out, _ = run_command('docker logs --tail 5 restaurant-ai')
    print(out)

    print("\nRecent Llama Logs:")
    code, out, _ = run_command('docker logs --tail 5 restaurant-ai-llama')
    print(out)

    print("\n" + "="*60)

if __name__ == "__main__":
    main()
```

### Fix Script

Save as `fix_docker_issues.sh`:

```bash
#!/bin/bash
# Fix common Docker issues

echo "Fixing Docker issues..."

# Stop containers
echo "Stopping containers..."
docker-compose down

# Remove orphaned containers
echo "Cleaning up..."
docker-compose rm -f

# Prune networks
docker network prune -f

# Update docker-compose.yml to enable AI
if [ -f "docker-compose.yml" ]; then
    echo "Updating docker-compose.yml..."
    sed -i 's/USE_LOCAL_AI:-false/USE_LOCAL_AI:-true/g' docker-compose.yml
fi

# Create .env if doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    echo "USE_LOCAL_AI=true" > .env
fi

# Restart containers
echo "Starting containers..."
docker-compose up -d

# Wait for startup
echo "Waiting for containers to start..."
sleep 10

# Check status
echo ""
echo "Container status:"
docker ps | grep restaurant

echo ""
echo "Waiting for health checks (this may take up to 15 minutes for llama-server)..."
echo "You can monitor with: docker-compose logs -f"
```

### Continuous Monitor Script

Save as `continuous_monitor.sh`:

```bash
#!/bin/bash
# Continuous monitoring script

INTERVAL=60  # Check every 60 seconds
LOG_FILE="docker_monitor.log"

echo "Starting continuous monitoring (interval: ${INTERVAL}s)"
echo "Logging to: $LOG_FILE"

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    # Check container status
    APP_STATUS=$(docker inspect -f '{{.State.Status}}' restaurant-ai 2>/dev/null || echo "not found")
    LLAMA_STATUS=$(docker inspect -f '{{.State.Status}}' restaurant-ai-llama 2>/dev/null || echo "not found")

    # Check health
    APP_HEALTH=$(docker inspect -f '{{.State.Health.Status}}' restaurant-ai 2>/dev/null || echo "no health")
    LLAMA_HEALTH=$(docker inspect -f '{{.State.Health.Status}}' restaurant-ai-llama 2>/dev/null || echo "no health")

    # Log status
    echo "[$TIMESTAMP] App: $APP_STATUS ($APP_HEALTH) | Llama: $LLAMA_STATUS ($LLAMA_HEALTH)" | tee -a "$LOG_FILE"

    # Alert if unhealthy
    if [ "$APP_HEALTH" != "healthy" ] || [ "$LLAMA_HEALTH" != "healthy" ]; then
        echo "⚠️  ALERT: Unhealthy containers detected!" | tee -a "$LOG_FILE"
        docker logs --tail 10 restaurant-ai 2>&1 | tee -a "$LOG_FILE"
        docker logs --tail 10 restaurant-ai-llama 2>&1 | tee -a "$LOG_FILE"
    fi

    sleep $INTERVAL
done
```

---

## Summary Checklist

When troubleshooting Docker issues, go through this checklist:

- [ ] Are containers running? (`docker ps`)
- [ ] Are containers healthy? (`docker inspect -f '{{.State.Health.Status}}'`)
- [ ] Are containers on the same network? (`docker network inspect`)
- [ ] Can containers resolve each other? (Test DNS)
- [ ] Can containers connect via HTTP? (Test curl/wget)
- [ ] Is `USE_LOCAL_AI` set to `true`? (Check env vars)
- [ ] Is `LLAMA_SERVER_URL` correct? (Should be `http://llama-server:8080`)
- [ ] Are ports properly exposed? (`docker port`)
- [ ] Is there enough memory? (`docker stats`)
- [ ] Are there errors in logs? (`docker logs`)
- [ ] Is the model file accessible? (Check volumes)
- [ ] Has llama-server finished loading? (Check logs for "startup complete")

---

## Quick Fix Commands

```bash
# Complete restart
docker-compose down && docker-compose up -d

# Restart specific service
docker-compose restart app
docker-compose restart llama-server

# Rebuild and restart
docker-compose down && docker-compose build --no-cache && docker-compose up -d

# View all logs
docker-compose logs -f

# Check resource usage
docker stats --no-stream

# Full cleanup and restart
docker-compose down -v
docker system prune -f
docker-compose up -d --build
```

---

## Additional Resources

- Docker Documentation: https://docs.docker.com/
- Docker Compose Documentation: https://docs.docker.com/compose/
- Docker Networking Guide: https://docs.docker.com/network/
- Docker Health Checks: https://docs.docker.com/engine/reference/builder/#healthcheck

---

**Last Updated:** 2026-04-06

**Version:** 1.0

**Maintainer:** System Administrator
