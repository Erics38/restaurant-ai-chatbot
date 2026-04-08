# Docker Diagnostics - PowerShell Version
# Run this to diagnose Docker container issues on Windows

function Print-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Print-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Print-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

# Header
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Restaurant AI Docker Diagnostics" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker is running
try {
    docker info | Out-Null
    Print-Success "Connected to Docker"
} catch {
    Print-Error "Docker is not running"
    Write-Host ""
    Write-Host "Please start Docker Desktop and try again."
    exit 1
}

# Check containers running
Print-Section "Container Status"

$appStatus = docker inspect -f '{{.State.Status}}' restaurant-ai 2>$null
$llamaStatus = docker inspect -f '{{.State.Status}}' restaurant-ai-llama 2>$null

if (-not $appStatus) { $appStatus = "not found" }
if (-not $llamaStatus) { $llamaStatus = "not found" }

Write-Host "App container: $appStatus"
Write-Host "Llama container: $llamaStatus"

if ($appStatus -ne "running") {
    Print-Error "App container not running"
    exit 1
}

if ($llamaStatus -ne "running") {
    Print-Error "Llama container not running"
    exit 1
}

Print-Success "Both containers are running"

# Health status
Print-Section "Health Status"

$appHealth = docker inspect -f '{{.State.Health.Status}}' restaurant-ai 2>$null
$llamaHealth = docker inspect -f '{{.State.Health.Status}}' restaurant-ai-llama 2>$null

if (-not $appHealth) { $appHealth = "no healthcheck" }
if (-not $llamaHealth) { $llamaHealth = "no healthcheck" }

Write-Host "App container health: $appHealth"
Write-Host "Llama container health: $llamaHealth"

if ($appHealth -eq "healthy" -and $llamaHealth -eq "healthy") {
    Print-Success "Both containers are healthy"
} elseif ($appHealth -eq "starting" -or $llamaHealth -eq "starting") {
    Print-Warning "Containers still starting up"
} else {
    Print-Warning "One or more containers unhealthy"
}

# Network
Print-Section "Network Configuration"

$appNetwork = docker inspect -f '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}' restaurant-ai
$llamaNetwork = docker inspect -f '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}' restaurant-ai-llama

Write-Host "App networks: $appNetwork"
Write-Host "Llama networks: $llamaNetwork"

if ($appNetwork -eq $llamaNetwork) {
    Print-Success "Containers on same network: $appNetwork"

    $appIP = docker inspect -f '{{range $key, $value := .NetworkSettings.Networks}}{{$value.IPAddress}} {{end}}' restaurant-ai
    $llamaIP = docker inspect -f '{{range $key, $value := .NetworkSettings.Networks}}{{$value.IPAddress}} {{end}}' restaurant-ai-llama

    Write-Host ""
    Write-Host "  App IP: $appIP"
    Write-Host "  Llama IP: $llamaIP"
} else {
    Print-Error "Containers not on same network!"
}

# Environment
Print-Section "Environment Configuration"

$useLocalAI = docker exec restaurant-ai printenv USE_LOCAL_AI 2>$null
$llamaURL = docker exec restaurant-ai printenv LLAMA_SERVER_URL 2>$null
$environment = docker exec restaurant-ai printenv ENVIRONMENT 2>$null

if (-not $useLocalAI) { $useLocalAI = "not set" }
if (-not $llamaURL) { $llamaURL = "not set" }
if (-not $environment) { $environment = "not set" }

Write-Host "Important environment variables:"
Write-Host "  USE_LOCAL_AI: $useLocalAI"
Write-Host "  LLAMA_SERVER_URL: $llamaURL"
Write-Host "  ENVIRONMENT: $environment"
Write-Host ""

if ($useLocalAI -eq "false") {
    Print-Warning "USE_LOCAL_AI is 'false' - AI features are disabled!"
    Write-Host "   Set USE_LOCAL_AI=true in docker-compose.yml or .env" -ForegroundColor Yellow
} else {
    Print-Success "USE_LOCAL_AI is enabled"
}

if ($llamaURL -like "*llama-server:8080*") {
    Print-Success "LLAMA_SERVER_URL correctly configured"
} elseif ($llamaURL -eq "not set") {
    Print-Warning "LLAMA_SERVER_URL not set"
} else {
    Print-Warning "LLAMA_SERVER_URL may be incorrect: $llamaURL"
}

# Ports
Print-Section "Port Mappings"

Write-Host "App ports:"
docker port restaurant-ai | ForEach-Object { Write-Host "  $_" }

Write-Host ""
Write-Host "Llama ports:"
docker port restaurant-ai-llama | ForEach-Object { Write-Host "  $_" }

Write-Host ""

$appPorts = docker port restaurant-ai
$llamaPorts = docker port restaurant-ai-llama

if ($appPorts -match "8000") {
    Print-Success "App port 8000 correctly exposed"
} else {
    Print-Error "App port 8000 not exposed"
}

if ($llamaPorts -match "8080") {
    Print-Success "Llama port 8080 correctly exposed"
} else {
    Print-Error "Llama port 8080 not exposed"
}

# Connectivity test
Print-Section "Connectivity Test"

Write-Host "Testing DNS resolution..."
try {
    $dnsResult = docker exec restaurant-ai python -c "import socket; print(socket.gethostbyname('llama-server'))" 2>$null
    if ($dnsResult) {
        Print-Success "DNS resolution working - llama-server resolves to: $dnsResult"
    } else {
        Print-Error "DNS resolution failed"
    }
} catch {
    Print-Error "DNS resolution failed: $_"
}

Write-Host ""
Write-Host "Testing HTTP connection to llama-server..."
try {
    docker exec restaurant-ai python -c "import urllib.request; urllib.request.urlopen('http://llama-server:8080/v1/models', timeout=5).read()" 2>&1 | Out-Null
    Print-Success "Successfully connected to llama-server API"

    # Get model info
    $modelInfo = docker exec restaurant-ai python -c "import urllib.request, json; data = json.loads(urllib.request.urlopen('http://llama-server:8080/v1/models', timeout=5).read()); print(data['data'][0]['id'] if data.get('data') else 'No models')" 2>$null
    if ($modelInfo) {
        Write-Host "  Loaded model: $modelInfo"
    }
} catch {
    Print-Error "HTTP connection failed"
}

# Resource usage
Print-Section "Resource Usage"

Write-Host "Container stats:"
docker stats --no-stream --format "table {{.Container}}`t{{.CPUPerc}}`t{{.MemUsage}}" restaurant-ai restaurant-ai-llama

# Recent logs
Print-Section "Recent Logs"

Write-Host "App container (last 10 lines):"
Write-Host "------------------------------------------------------------"
docker logs --tail 10 restaurant-ai 2>&1

Write-Host ""
Write-Host "Llama container (last 10 lines):"
Write-Host "------------------------------------------------------------"
docker logs --tail 10 restaurant-ai-llama 2>&1

# Summary
Print-Section "Diagnostic Complete"

Write-Host "Check the output above for any ❌ or ⚠️  symbols"
Write-Host ""
Write-Host "Common issues:"
Write-Host "  1. USE_LOCAL_AI=false - AI is disabled"
Write-Host "  2. Unhealthy containers - check health check logs"
Write-Host "  3. Network issues - verify containers on same network"
Write-Host "  4. Connection timeouts - llama-server may still be loading model"
Write-Host ""
Write-Host "For detailed tests, run:"
Write-Host "  pip install -r requirements-test.txt"
Write-Host "  pytest test_docker_health.py -v -s"
Write-Host ""
