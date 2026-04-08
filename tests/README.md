# Docker Health & Connectivity Tests

Comprehensive test suite for diagnosing Docker container issues in the Restaurant AI Chatbot.

## Quick Start

### 1. Run Quick Diagnostics (No dependencies needed)

```bash
cd tests
python docker_diagnostic.py
```

This will show you:
- Container running status
- Health check status
- Network configuration
- Environment variables
- Port mappings
- Resource usage
- Connectivity tests
- Recent logs

### 2. Run Full Test Suite

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest test_docker_health.py -v -s

# Run specific test class
pytest test_docker_health.py::TestDockerContainerHealth -v -s

# Run specific test
pytest test_docker_health.py::TestLlamaServerConnectivity::test_llama_server_from_host -v
```

## Test Categories

### Container Health Tests
- `test_containers_running` - Verify both containers are running
- `test_container_health_status` - Check health check results
- `test_container_restart_count` - Detect crash loops
- `test_container_uptime` - Check if containers recently restarted
- `test_container_exit_code` - Check for error exits

### Network Tests
- `test_containers_on_same_network` - Verify network configuration
- `test_network_exists` - Check if restaurant network exists
- `test_network_driver` - Verify bridge network driver
- `test_dns_resolution_between_containers` - Test hostname resolution
- `test_network_connectivity_ping` - Test socket connectivity
- `test_container_ip_addresses` - Display IP addresses

### Connectivity Tests
- `test_llama_server_from_host` - Test from host machine
- `test_llama_server_from_app_container` - Test from app container
- `test_llama_server_chat_completion` - Test AI functionality
- `test_llama_server_response_time` - Measure response times

### Resource Tests
- `test_memory_limits` - Check memory configuration
- `test_cpu_limits` - Check CPU configuration
- `test_container_stats` - Real-time resource usage

### Volume Tests
- `test_volume_mounts` - Verify volume configuration
- `test_model_file_exists` - Check if model file is accessible

### Environment Tests
- `test_use_local_ai_setting` - Check if AI is enabled
- `test_all_environment_variables` - Display all env vars

### Log Tests
- `test_app_container_logs` - Check app logs for errors
- `test_llama_container_logs` - Check llama logs
- `test_logs_for_oom_errors` - Detect memory issues

### Docker Compose Tests
- `test_compose_project_name` - Verify project configuration
- `test_compose_service_names` - Verify service names

## Common Issues & Solutions

### Issue 1: USE_LOCAL_AI is false

**Symptom:** AI responses are template-based, not using the LLM

**Detection:**
```bash
python docker_diagnostic.py
# Look for: "⚠️  USE_LOCAL_AI is 'false' - AI features are disabled!"
```

**Solution:**
```bash
# Option 1: Edit docker-compose.yml
# Change: - USE_LOCAL_AI=${USE_LOCAL_AI:-false}
# To:     - USE_LOCAL_AI=${USE_LOCAL_AI:-true}

# Option 2: Set in .env file
echo "USE_LOCAL_AI=true" >> .env

# Restart containers
docker-compose restart app
```

### Issue 2: Containers unhealthy

**Symptom:** `docker ps` shows "(unhealthy)" status

**Detection:**
```bash
pytest test_docker_health.py::TestDockerContainerHealth::test_container_health_status -v -s
```

**Common causes:**
- Health check endpoint not responding
- Container still initializing
- Port not accessible

**Solution:**
```bash
# Check health check logs
docker inspect restaurant-ai --format='{{json .State.Health}}' | python -m json.tool
docker inspect restaurant-ai-llama --format='{{json .State.Health}}' | python -m json.tool

# Wait for startup (llama-server has 900s start_period)
# If still unhealthy after startup period, check logs
docker logs restaurant-ai
docker logs restaurant-ai-llama
```

### Issue 3: Connection timeout

**Symptom:** "Error calling llama-server" in logs

**Detection:**
```bash
pytest test_docker_health.py::TestLlamaServerConnectivity::test_llama_server_from_app_container -v -s
```

**Common causes:**
- Containers on different networks
- DNS not resolving
- llama-server still loading model
- Firewall blocking connection

**Solution:**
```bash
# Test DNS resolution
docker exec restaurant-ai python -c "import socket; print(socket.gethostbyname('llama-server'))"

# Test HTTP connection
docker exec restaurant-ai python -c "import urllib.request; print(urllib.request.urlopen('http://llama-server:8080/v1/models', timeout=5).read())"

# If DNS fails, check network
docker network inspect restaurant-ai-chatbot_restaurant-network

# If still failing, restart containers
docker-compose down && docker-compose up -d
```

### Issue 4: Model not loaded

**Symptom:** llama-server returns empty model list

**Detection:**
```bash
pytest test_docker_health.py::TestDockerVolumes::test_model_file_exists -v -s
```

**Solution:**
```bash
# Check if model file exists in container
docker exec restaurant-ai-llama ls -lh /models/

# Check volume mount
docker inspect restaurant-ai-llama --format='{{json .Mounts}}' | python -m json.tool

# Verify model file on host
ls -lh ./models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf

# If missing, download the model
# (Add download instructions based on your setup)
```

### Issue 5: High memory usage

**Symptom:** System running slow, containers using too much RAM

**Detection:**
```bash
pytest test_docker_health.py::TestDockerResources::test_container_stats -v -s
```

**Solution:**
```bash
# Check current usage
docker stats --no-stream

# Adjust memory limits in docker-compose.yml
# For llama-server:
#   limits:
#     memory: 9G  # Reduce if needed
#   reservations:
#     memory: 7G  # Reduce if needed

# Restart with new limits
docker-compose down && docker-compose up -d
```

### Issue 6: Containers not on same network

**Symptom:** Cannot resolve llama-server hostname

**Detection:**
```bash
pytest test_docker_health.py::TestDockerNetwork::test_containers_on_same_network -v -s
```

**Solution:**
```bash
# Recreate containers with docker-compose
docker-compose down
docker-compose up -d

# This ensures they're on the same network
```

## Monitoring & Debugging

### Watch logs in real-time

```bash
# Both containers
docker-compose logs -f

# Just app
docker logs -f restaurant-ai

# Just llama-server
docker logs -f restaurant-ai-llama
```

### Execute commands in containers

```bash
# App container
docker exec -it restaurant-ai bash
docker exec -it restaurant-ai python

# Llama container
docker exec -it restaurant-ai-llama bash
```

### Check resource usage continuously

```bash
docker stats restaurant-ai restaurant-ai-llama
```

### Inspect container configuration

```bash
# Full configuration
docker inspect restaurant-ai
docker inspect restaurant-ai-llama

# Specific fields
docker inspect restaurant-ai --format='{{.State.Status}}'
docker inspect restaurant-ai --format='{{json .NetworkSettings.Networks}}'
docker inspect restaurant-ai --format='{{json .Config.Env}}'
```

## Continuous Monitoring

You can run the diagnostic script periodically:

```bash
# Run every 5 minutes
while true; do
  python docker_diagnostic.py
  sleep 300
done
```

Or use pytest with watch:

```bash
pip install pytest-watch
ptw test_docker_health.py
```

## Integration with CI/CD

Add to your CI pipeline:

```yaml
# .github/workflows/docker-health.yml
name: Docker Health Check

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start containers
        run: docker-compose up -d
      - name: Wait for healthy
        run: sleep 60
      - name: Install test deps
        run: pip install -r tests/requirements-test.txt
      - name: Run diagnostics
        run: python tests/docker_diagnostic.py
      - name: Run tests
        run: pytest tests/test_docker_health.py -v
```

## Contributing

When adding new tests:

1. Follow the existing test class structure
2. Add clear docstrings
3. Include helpful print statements for debugging
4. Test both success and failure cases
5. Update this README with new test documentation
