#!/bin/bash
#
# Quick Docker diagnostics script (bash version)
# Run this to get a snapshot of Docker container health
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_section() {
    echo ""
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# Header
echo ""
echo "============================================================"
echo "  Restaurant AI Docker Diagnostics"
echo "============================================================"
echo ""

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running"
    echo ""
    echo "Please start Docker and try again."
    exit 1
fi

print_success "Connected to Docker"

# Check containers running
print_section "Container Status"

APP_STATUS=$(docker inspect -f '{{.State.Status}}' restaurant-ai 2>/dev/null || echo "not found")
LLAMA_STATUS=$(docker inspect -f '{{.State.Status}}' restaurant-ai-llama 2>/dev/null || echo "not found")

echo "App container: $APP_STATUS"
echo "Llama container: $LLAMA_STATUS"

if [ "$APP_STATUS" != "running" ]; then
    print_error "App container not running"
    exit 1
fi

if [ "$LLAMA_STATUS" != "running" ]; then
    print_error "Llama container not running"
    exit 1
fi

print_success "Both containers are running"

# Health status
print_section "Health Status"

APP_HEALTH=$(docker inspect -f '{{.State.Health.Status}}' restaurant-ai 2>/dev/null || echo "no healthcheck")
LLAMA_HEALTH=$(docker inspect -f '{{.State.Health.Status}}' restaurant-ai-llama 2>/dev/null || echo "no healthcheck")

echo "App container health: $APP_HEALTH"
echo "Llama container health: $LLAMA_HEALTH"

if [ "$APP_HEALTH" = "healthy" ] && [ "$LLAMA_HEALTH" = "healthy" ]; then
    print_success "Both containers are healthy"
elif [ "$APP_HEALTH" = "starting" ] || [ "$LLAMA_HEALTH" = "starting" ]; then
    print_warning "Containers still starting up"
else
    print_warning "One or more containers unhealthy"
fi

# Network
print_section "Network Configuration"

APP_NETWORK=$(docker inspect -f '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}' restaurant-ai)
LLAMA_NETWORK=$(docker inspect -f '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}' restaurant-ai-llama)

echo "App networks: $APP_NETWORK"
echo "Llama networks: $LLAMA_NETWORK"

if [ "$APP_NETWORK" = "$LLAMA_NETWORK" ]; then
    print_success "Containers on same network: $APP_NETWORK"

    APP_IP=$(docker inspect -f '{{range $key, $value := .NetworkSettings.Networks}}{{$value.IPAddress}} {{end}}' restaurant-ai)
    LLAMA_IP=$(docker inspect -f '{{range $key, $value := .NetworkSettings.Networks}}{{$value.IPAddress}} {{end}}' restaurant-ai-llama)

    echo ""
    echo "  App IP: $APP_IP"
    echo "  Llama IP: $LLAMA_IP"
else
    print_error "Containers not on same network!"
fi

# Environment
print_section "Environment Configuration"

USE_LOCAL_AI=$(docker exec restaurant-ai printenv USE_LOCAL_AI 2>/dev/null || echo "not set")
LLAMA_URL=$(docker exec restaurant-ai printenv LLAMA_SERVER_URL 2>/dev/null || echo "not set")
ENVIRONMENT=$(docker exec restaurant-ai printenv ENVIRONMENT 2>/dev/null || echo "not set")

echo "Important environment variables:"
echo "  USE_LOCAL_AI: $USE_LOCAL_AI"
echo "  LLAMA_SERVER_URL: $LLAMA_URL"
echo "  ENVIRONMENT: $ENVIRONMENT"
echo ""

if [ "$USE_LOCAL_AI" = "false" ]; then
    print_warning "USE_LOCAL_AI is 'false' - AI features are disabled!"
    echo "   Set USE_LOCAL_AI=true in docker-compose.yml or .env"
else
    print_success "USE_LOCAL_AI is enabled"
fi

if [[ "$LLAMA_URL" == *"llama-server:8080"* ]]; then
    print_success "LLAMA_SERVER_URL correctly configured"
elif [ "$LLAMA_URL" = "not set" ]; then
    print_warning "LLAMA_SERVER_URL not set"
else
    print_warning "LLAMA_SERVER_URL may be incorrect: $LLAMA_URL"
fi

# Ports
print_section "Port Mappings"

APP_PORTS=$(docker port restaurant-ai)
LLAMA_PORTS=$(docker port restaurant-ai-llama)

echo "App ports:"
echo "$APP_PORTS" | sed 's/^/  /'

echo ""
echo "Llama ports:"
echo "$LLAMA_PORTS" | sed 's/^/  /'

echo ""

if echo "$APP_PORTS" | grep -q "8000"; then
    print_success "App port 8000 correctly exposed"
else
    print_error "App port 8000 not exposed"
fi

if echo "$LLAMA_PORTS" | grep -q "8080"; then
    print_success "Llama port 8080 correctly exposed"
else
    print_error "Llama port 8080 not exposed"
fi

# Connectivity test
print_section "Connectivity Test"

echo "Testing DNS resolution..."
if docker exec restaurant-ai python -c "import socket; print(socket.gethostbyname('llama-server'))" 2>/dev/null; then
    print_success "DNS resolution working"
else
    print_error "DNS resolution failed"
fi

echo ""
echo "Testing HTTP connection to llama-server..."
if docker exec restaurant-ai python -c "import urllib.request; urllib.request.urlopen('http://llama-server:8080/v1/models', timeout=5).read()" > /dev/null 2>&1; then
    print_success "Successfully connected to llama-server API"

    # Get model info
    MODEL_INFO=$(docker exec restaurant-ai python -c "import urllib.request, json; data = json.loads(urllib.request.urlopen('http://llama-server:8080/v1/models', timeout=5).read()); print(data['data'][0]['id'] if data.get('data') else 'No models')" 2>/dev/null || echo "Error getting model info")
    echo "  Loaded model: $MODEL_INFO"
else
    print_error "HTTP connection failed"
fi

# Resource usage
print_section "Resource Usage"

echo "Container stats:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" restaurant-ai restaurant-ai-llama

# Recent logs
print_section "Recent Logs"

echo "App container (last 10 lines):"
echo "------------------------------------------------------------"
docker logs --tail 10 restaurant-ai 2>&1

echo ""
echo "Llama container (last 10 lines):"
echo "------------------------------------------------------------"
docker logs --tail 10 restaurant-ai-llama 2>&1

# Summary
print_section "Diagnostic Complete"

echo "Check the output above for any ❌ or ⚠️  symbols"
echo ""
echo "Common issues:"
echo "  1. USE_LOCAL_AI=false - AI is disabled"
echo "  2. Unhealthy containers - check health check logs"
echo "  3. Network issues - verify containers on same network"
echo "  4. Connection timeouts - llama-server may still be loading model"
echo ""
echo "For detailed tests, run:"
echo "  pip install -r requirements-test.txt"
echo "  pytest test_docker_health.py -v -s"
echo ""
