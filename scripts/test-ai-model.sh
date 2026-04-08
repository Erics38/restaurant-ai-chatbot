#!/bin/bash
# Test AI Model on EC2
# This script tests the llama-server directly to verify AI is working

echo "=========================================="
echo "Testing AI Model (Llama-3-8B)"
echo "=========================================="
echo ""

# Test 1: Check if llama-server is running
echo "[1/4] Checking llama-server health..."
if curl -f http://localhost:8080/health 2>/dev/null; then
    echo "✓ llama-server is healthy"
else
    echo "✗ llama-server is not responding"
    exit 1
fi
echo ""

# Test 2: List available models
echo "[2/4] Checking available models..."
curl -s http://localhost:8080/v1/models | python3 -m json.tool
echo ""

# Test 3: Test AI chat completion
echo "[3/4] Testing AI chat completion..."
echo "Question: What burgers do you have?"
echo ""
curl -s -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are Tobi, a friendly restaurant AI assistant for The Common House."},
      {"role": "user", "content": "What burgers do you have?"}
    ],
    "max_tokens": 150,
    "temperature": 0.7
  }' | python3 -c "import sys, json; response = json.load(sys.stdin); print('AI Response:', response['choices'][0]['message']['content'])"
echo ""
echo ""

# Test 4: Check app environment
echo "[4/4] Checking app AI configuration..."
docker compose exec -T app env | grep USE_LOCAL_AI
docker compose exec -T app env | grep LLAMA_SERVER_URL
echo ""

echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "If USE_LOCAL_AI=false, enable it with:"
echo "  export USE_LOCAL_AI=true"
echo "  docker compose up -d app"
