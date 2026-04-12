# Tobi — Restaurant AI Chatbot

An AI-powered restaurant chatbot you can deploy in minutes. Tobi knows your menu, handles customer questions, and connects to your choice of AI backend — AWS Bedrock, a local model, or your own custom endpoint.

[![Docker Build](https://github.com/Erics38/restaurant-ai-chatbot/actions/workflows/docker.yml/badge.svg)](https://github.com/Erics38/restaurant-ai-chatbot/actions/workflows/docker.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## What it does

- **Menu-aware chat** — Tobi knows every item, price, and ingredient and can make recommendations
- **Three AI backends** — AWS Bedrock (Claude), local Llama model, or your own custom endpoint
- **Bring your own menu** — point to a JSON URL and Tobi adopts your restaurant's menu instantly
- **Bring your own model** — connect any OpenAI-compatible or custom model via a single endpoint
- **Template fallback** — if AI is unavailable, Tobi answers instantly from keyword templates
- **Persistent sessions** — conversation history stored in SQLite across page refreshes
- **One-command AWS deploy** — CloudFormation template spins up everything automatically

---

## Deploy to AWS in 5 minutes

The fastest way to get Tobi running is the CloudFormation template. It creates a VPC, EC2 instance, IAM role, and starts the Docker container automatically.

### Prerequisites

1. **Enable Bedrock model access** in your AWS account:
   AWS Console → Amazon Bedrock → Model access → Request access for Claude Sonnet (takes ~2 minutes)

2. **AWS CLI configured** with your credentials

### Deploy

```bash
aws cloudformation deploy \
  --template-file cloudformation/tobi-chatbot.yml \
  --stack-name tobi-chatbot \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

When it completes (~5 minutes), get your URL:

```bash
aws cloudformation describe-stacks \
  --stack-name tobi-chatbot \
  --query 'Stacks[0].Outputs' \
  --output table
```

Open the `ApplicationURL` in your browser — Tobi is live.

### CloudFormation parameters

| Parameter | Default | Description |
|---|---|---|
| `RestaurantName` | The Common House | Name shown in chat responses |
| `BedrockRegion` | us-east-1 | AWS region with Claude access |
| `BedrockModelId` | Claude Sonnet 4.5 | Bedrock model to use |
| `MenuUrl` | _(blank)_ | URL of your custom menu JSON — leave blank for the built-in menu |
| `CustomBackendUrl` | _(blank)_ | URL of your own AI endpoint — leave blank to use Bedrock |

To deploy with a custom menu and/or custom model:

```bash
aws cloudformation deploy \
  --template-file cloudformation/tobi-chatbot.yml \
  --stack-name tobi-chatbot \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
      RestaurantName="Joes Diner" \
      MenuUrl="https://example.com/menu.json" \
      CustomBackendUrl="http://my-model-server/chat"
```

---

## Plug in your own menu

Create a public JSON file (GitHub Gist works great) with this structure:

```json
{
  "restaurant_name": "Joes Diner",
  "starters": [
    {"name": "Chicken Wings", "description": "Buffalo sauce, ranch dip", "price": 12.00}
  ],
  "mains": [
    {"name": "Classic Burger", "description": "Beef patty, cheddar, lettuce, tomato", "price": 15.00}
  ],
  "desserts": [
    {"name": "Cheesecake", "description": "New York style, berry compote", "price": 8.00}
  ],
  "drinks": [
    {"name": "Craft Beer", "description": "Ask your server for today's selection", "price": 7.00}
  ]
}
```

Pass the raw URL as `MenuUrl` when deploying. Tobi loads the menu at startup and falls back to the built-in Common House menu if the URL is unreachable.

---

## Plug in your own model

Any model or container that can accept a POST request works. Your endpoint receives:

```json
{
  "message": "what burgers do you have?",
  "session_id": "abc-123",
  "history": [
    {"role": "user", "content": "hi"},
    {"role": "assistant", "content": "Hey! Welcome to Joes Diner!"}
  ]
}
```

And must return:

```json
{
  "response": "We have the Classic Burger for $15 — beef patty, cheddar, lettuce, and tomato. Want to add it to your order?"
}
```

Pass your endpoint URL as `CustomBackendUrl` when deploying. Tobi automatically sets `AI_BACKEND=custom` and routes all chat through your endpoint, falling back to keyword templates if your server is unreachable.

### Testing locally with a custom model

Run Tobi locally with Docker and point it at your local model server:

```bash
docker run -d \
  --name tobi \
  -p 8000:8000 \
  -e AI_BACKEND=custom \
  -e CUSTOM_BACKEND_URL=http://host.docker.internal:11434/chat \
  -e RESTAURANT_NAME="My Restaurant" \
  ghcr.io/erics38/restaurant-ai-chatbot:latest
```

Open http://localhost:8000 to test.

---

## Run locally (no AWS)

```bash
# Clone
git clone https://github.com/Erics38/restaurant-ai-chatbot.git
cd restaurant-ai-chatbot

# Start with Docker (uses template fallback — no AI needed)
docker-compose up -d

# Or run directly
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `RESTAURANT_NAME` | The Common House | Restaurant name shown in responses |
| `AI_BACKEND` | template | `template` / `bedrock` / `custom` |
| `CUSTOM_BACKEND_URL` | _(blank)_ | Your model endpoint URL |
| `MENU_URL` | _(blank)_ | Your menu JSON URL |
| `AWS_REGION` | us-east-1 | Bedrock region |
| `BEDROCK_MODEL_ID` | Claude Sonnet 4.5 | Bedrock model ID |
| `ENVIRONMENT` | development | `development` / `production` |
| `ALLOWED_ORIGINS` | * | CORS origins |

---

## AI Backends

| Backend | How to activate | Best for |
|---|---|---|
| **Template** | `AI_BACKEND=template` | Fast demos, no AI needed |
| **Bedrock** | `AI_BACKEND=bedrock` (default on AWS) | Production — Claude via AWS |
| **Llama (local)** | `AI_BACKEND=llama` + `LLAMA_SERVER_URL` | Self-hosted open source model |
| **Custom** | `AI_BACKEND=custom` + `CUSTOM_BACKEND_URL` | Your own model or container |

All backends fall back to template responses automatically if unavailable.

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root — serves the chat UI |
| `GET` | `/health` | Health check |
| `GET` | `/menu` | Full menu as JSON |
| `POST` | `/chat` | Send a message to Tobi |
| `GET` | `/chat/history/{session_id}` | Conversation history |

**Swagger UI:** http://localhost:8000/api/docs (development mode only)

### Chat request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what burgers do you have?"}'
```

```json
{
  "response": "Oh dude, the House Smash Burger is gnarly! Double patty, cheddar, caramelized onion — $16. Want me to add it?",
  "session_id": "abc-123",
  "restaurant": "The Common House"
}
```

---

## Project structure

```
restaurant-ai-chatbot/
├── app/
│   ├── main.py           # FastAPI app and endpoints
│   ├── config.py         # All configuration via env vars
│   ├── tobi_ai.py        # AI backends and dispatcher
│   ├── menu_data.py      # Menu loader (built-in + MENU_URL)
│   ├── prompts.py        # System prompts for AI backends
│   ├── models.py         # Pydantic and SQLAlchemy models
│   └── database.py       # SQLite session management
├── static/
│   └── restaurant_chat.html  # Chat UI
├── cloudformation/
│   └── tobi-chatbot.yml  # AWS CloudFormation template
├── tests/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) — Full deployment guide including AWS CloudFormation
- [ARCHITECTURE.md](ARCHITECTURE.md) — How the backends and dispatcher work
- [BEDROCK_INTEGRATION.md](BEDROCK_INTEGRATION.md) — AWS Bedrock setup details

---

## Contributing

1. Fork and clone the repository
2. `pip install -r requirements.txt`
3. `pip install pytest black flake8`
4. Make your changes and run `pytest tests/test_main.py tests/test_models.py tests/test_tobi_ai.py`
5. Open a pull request

---

Built with FastAPI, Docker, and AWS Bedrock.
