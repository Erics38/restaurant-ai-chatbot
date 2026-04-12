# Deployment Guide

---

## Option 1 — AWS CloudFormation (Recommended)

The CloudFormation template in `cloudformation/tobi-chatbot.yml` deploys everything automatically:
- VPC, subnet, internet gateway, and security group
- EC2 t2.micro instance (free tier eligible)
- IAM role scoped to Bedrock only
- Docker container with health checks and auto-restart on reboot

### Prerequisites

1. **Enable Bedrock model access**:
   AWS Console → Amazon Bedrock → Model access → Request access for Claude Sonnet (~2 minutes)

2. **AWS CLI installed and configured**:
   ```bash
   aws configure
   # Enter your Access Key ID, Secret Access Key, and region (us-east-1)
   ```

### Deploy

```bash
# Basic deploy — uses Bedrock + built-in Common House menu
aws cloudformation deploy \
  --template-file cloudformation/tobi-chatbot.yml \
  --stack-name tobi-chatbot \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

```bash
# Deploy with your own restaurant name and menu
aws cloudformation deploy \
  --template-file cloudformation/tobi-chatbot.yml \
  --stack-name tobi-chatbot \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
      RestaurantName="Joes Diner" \
      MenuUrl="https://gist.githubusercontent.com/.../menu.json"
```

```bash
# Deploy with your own AI model endpoint
aws cloudformation deploy \
  --template-file cloudformation/tobi-chatbot.yml \
  --stack-name tobi-chatbot \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
      CustomBackendUrl="http://my-model-server.com/chat"
```

### Get your URL

```bash
aws cloudformation describe-stacks \
  --stack-name tobi-chatbot \
  --query 'Stacks[0].Outputs' \
  --output table
```

Open the `ApplicationURL` in your browser.

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `RestaurantName` | The Common House | Shown in Tobi's chat responses |
| `BedrockRegion` | us-east-1 | AWS region — must have Claude access |
| `BedrockModelId` | Claude Sonnet 4.5 | Bedrock model ID |
| `MenuUrl` | _(blank)_ | URL of your custom menu JSON. Leave blank for built-in menu |
| `CustomBackendUrl` | _(blank)_ | URL of your own AI endpoint. Leave blank to use Bedrock |

### Custom menu format

Host a JSON file publicly (GitHub Gist works) with this structure:

```json
{
  "restaurant_name": "Joes Diner",
  "starters": [
    {"name": "Wings", "description": "Buffalo sauce", "price": 12.00}
  ],
  "mains": [
    {"name": "Burger", "description": "Beef patty, cheddar", "price": 15.00}
  ],
  "desserts": [
    {"name": "Cheesecake", "description": "Berry compote", "price": 8.00}
  ],
  "drinks": [
    {"name": "Craft Beer", "description": "Ask your server", "price": 7.00}
  ]
}
```

### Custom AI backend contract

Your endpoint must accept POST requests:

```
POST https://your-model-server.com/chat
Content-Type: application/json

{
  "message": "what do you have?",
  "session_id": "abc-123",
  "history": [
    {"role": "user", "content": "hi"},
    {"role": "assistant", "content": "Hey! Welcome!"}
  ]
}
```

And return:

```json
{"response": "We have wings for $12 and burgers for $15!"}
```

Tobi falls back to keyword templates automatically if your server is unreachable.

### Tear down

```bash
aws cloudformation delete-stack --stack-name tobi-chatbot
```

### Cost

| | Cost |
|---|---|
| EC2 t2.micro (free tier) | $0 for first 12 months, ~$8.50/mo after |
| Bedrock (Claude Sonnet) | ~$1.50/mo at typical usage |
| **Total** | **~$0–10/mo** |

---

## Option 2 — Docker (Local or any server)

```bash
# Pull and run — template mode (no AI)
docker run -d \
  --name tobi \
  -p 8000:8000 \
  -e RESTAURANT_NAME="My Restaurant" \
  ghcr.io/erics38/restaurant-ai-chatbot:latest

# With Bedrock
docker run -d \
  --name tobi \
  -p 8000:8000 \
  -e AI_BACKEND=bedrock \
  -e AWS_REGION=us-east-1 \
  -e BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  -e RESTAURANT_NAME="My Restaurant" \
  ghcr.io/erics38/restaurant-ai-chatbot:latest

# With your own model
docker run -d \
  --name tobi \
  -p 8000:8000 \
  -e AI_BACKEND=custom \
  -e CUSTOM_BACKEND_URL=http://host.docker.internal:11434/chat \
  -e RESTAURANT_NAME="My Restaurant" \
  ghcr.io/erics38/restaurant-ai-chatbot:latest

# With your own menu
docker run -d \
  --name tobi \
  -p 8000:8000 \
  -e MENU_URL=https://example.com/menu.json \
  -e RESTAURANT_NAME="My Restaurant" \
  ghcr.io/erics38/restaurant-ai-chatbot:latest
```

Open http://localhost:8000

### Docker Compose

```bash
git clone https://github.com/Erics38/restaurant-ai-chatbot.git
cd restaurant-ai-chatbot
docker-compose up -d
```

---

## Option 3 — Local development

```bash
git clone https://github.com/Erics38/restaurant-ai-chatbot.git
cd restaurant-ai-chatbot
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `RESTAURANT_NAME` | The Common House | Name shown in responses |
| `AI_BACKEND` | template | `template` / `bedrock` / `llama` / `custom` |
| `CUSTOM_BACKEND_URL` | _(blank)_ | Your model endpoint |
| `MENU_URL` | _(blank)_ | Your menu JSON URL |
| `AWS_REGION` | us-east-1 | Bedrock region |
| `BEDROCK_MODEL_ID` | Claude Sonnet 4.5 | Bedrock model ID |
| `LLAMA_SERVER_URL` | _(blank)_ | llama-server URL (for llama backend) |
| `ENVIRONMENT` | development | `development` / `production` |
| `ALLOWED_ORIGINS` | * | CORS allowed origins |
| `LOG_LEVEL` | INFO | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## Troubleshooting

**Stack creation failed**
```bash
aws cloudformation describe-stack-events \
  --stack-name tobi-chatbot \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
```

**App not responding after deploy**
```bash
# Check container is running
docker ps

# Check logs
docker logs tobi
```

**Bedrock access denied**
- Confirm model access is enabled in AWS Console → Bedrock → Model access
- Confirm the EC2 instance has the IAM role attached (CloudFormation does this automatically)

**Custom menu not loading**
- Ensure the URL is publicly accessible (no auth required)
- Verify the JSON matches the expected structure
- Check app logs — Tobi falls back to the default menu and logs the error

**Custom backend not responding**
- Tobi falls back to templates automatically and logs the error
- Check your endpoint accepts POST with `Content-Type: application/json`
- Verify it returns `{"response": "..."}` 

---

For Bedrock-specific setup see [BEDROCK_INTEGRATION.md](BEDROCK_INTEGRATION.md).
