#!/bin/bash
# EC2 Setup Script with Full AI Support
# This script sets up the Restaurant AI Chatbot with Llama-3-8B AI model on EC2
# Run this on a fresh Ubuntu 24.04 instance

set -e  # Exit on any error

echo "=========================================="
echo "Restaurant AI Setup with Full AI Model"
echo "=========================================="
echo ""

# Update system
echo "[1/8] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Docker and Docker Compose
echo "[2/8] Installing Docker..."
sudo apt-get install -y docker.io docker-compose-v2 git curl wget

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Enable and start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Install Python for testing
echo "[3/8] Installing Python..."
sudo apt-get install -y python3 python3-venv python3-pip build-essential cmake

# Clone repository
echo "[4/8] Cloning restaurant-ai-chatbot..."
cd /home/ubuntu
if [ ! -d "restaurant-ai-chatbot" ]; then
    git clone https://github.com/Erics38/restaurant-ai-chatbot.git
fi
cd restaurant-ai-chatbot

# Fix permissions
sudo mkdir -p logs data models
sudo chown -R ubuntu:ubuntu logs data models

# Download Llama-3-8B AI model (4.92GB)
echo "[5/8] Downloading Llama-3-8B AI model (4.92GB)..."
if [ ! -f "models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf" ]; then
    wget -O models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf \
      https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf
    echo "✓ Model downloaded successfully"
else
    echo "✓ Model already exists, skipping download"
fi

# Build custom llama-server Docker image
echo "[6/8] Building llama-server Docker image..."
cat > Dockerfile.llamacpp << 'EOF'
FROM python:3.11-slim

# Install build dependencies for llama-cpp-python
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Install llama-cpp-python with server
RUN pip install --no-cache-dir llama-cpp-python[server]

EXPOSE 8080

CMD ["python", "-m", "llama_cpp.server"]
EOF

docker build -f Dockerfile.llamacpp -t local-llama-server .

# Create docker-compose override for AI mode
echo "[7/8] Creating docker-compose override for AI mode..."
cat > docker-compose.override.yml << 'EOF'
version: '3.8'

services:
  app:
    environment:
      - USE_LOCAL_AI=true

  llama-server:
    image: local-llama-server
    command:
      - "python"
      - "-m"
      - "llama_cpp.server"
      - "--model"
      - "/models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
      - "--host"
      - "0.0.0.0"
      - "--port"
      - "8080"
      - "--n-ctx"
      - "4096"
    volumes:
      - ./models:/models:ro
EOF

# Start Docker Compose with AI
echo "[8/8] Starting application with AI..."
docker compose up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 15

# Check health
echo ""
echo "=========================================="
echo "Checking Service Health"
echo "=========================================="

if curl -f http://localhost:8000/health; then
    echo ""
    echo "✓ App is healthy"
else
    echo "✗ App health check failed"
fi

if curl -f http://localhost:8080/health; then
    echo "✓ AI model server is healthy"
else
    echo "✗ AI model server health check failed"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "Access the application:"
echo "  Web UI:   http://${PUBLIC_IP}:8000/static/restaurant_chat.html"
echo "  API Docs: http://${PUBLIC_IP}:8000/api/docs"
echo "  Health:   http://${PUBLIC_IP}:8000/health"
echo ""
echo "Test AI model:"
echo "  curl http://localhost:8080/v1/models"
echo ""
echo "View logs:"
echo "  docker compose logs app"
echo "  docker compose logs llama-server"
echo ""
