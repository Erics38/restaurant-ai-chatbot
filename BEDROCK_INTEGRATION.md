# AWS Bedrock Integration Guide

This guide walks an engineer through switching Tobi's AI backend from the local
Llama-3 model to AWS Bedrock Claude.  Follow the steps in order — each step is
safe to complete without breaking the running app.

---

## Why Bedrock?

| | Template mode | Local Llama-3 | AWS Bedrock |
|---|---|---|---|
| **RAM required** | ~100 MB | ~9 GB | ~100 MB |
| **Cold start** | Instant | ~15 min | ~2–5 s |
| **Model file** | None | 4.9 GB GGUF | None |
| **Cost** | Free | Free (EC2 cost only) | Pay-per-token (~$0.003/1K tokens) |
| **Response quality** | Keyword templates | Llama-3-8B | Claude Sonnet 4.5 |
| **Ops complexity** | Minimal | Moderate (GPU/RAM sizing) | Minimal |
| **Internet required** | No | No | Yes |

**Choose Bedrock when:** engineers don't have a machine with 9 GB free RAM, or
you want Claude-quality responses without managing a local model.

**Keep Llama-3 when:** you need fully offline operation or want zero API costs.

---

## Step 1 — AWS Setup

### 1a. Request model access

Bedrock requires explicit per-model access approval before you can call it.

1. Sign in to the [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **Amazon Bedrock** → **Model access** (left sidebar)
3. Click **Modify model access**
4. Find **Anthropic → Claude Sonnet 4.5** and check the box
5. Submit — approval is typically instant for Claude Sonnet

> Repeat for any additional models you plan to use.  Access is per-region —
> if you change `AWS_REGION`, you must request access again in that region.

### 1b. Create an IAM role for EC2 (production — recommended)

Using an IAM role means zero credentials stored anywhere.  boto3 discovers
temporary credentials automatically from the EC2 instance metadata service.

**Create the role:**

1. AWS Console → **IAM** → **Roles** → **Create role**
2. Trusted entity: **AWS service → EC2**
3. Skip the managed policies — add an inline policy instead (least privilege):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
        "arn:aws:bedrock:us-east-1:<YOUR-ACCOUNT-ID>:inference-profile/us.anthropic.claude-sonnet-4-5-20250929-v1:0"
      ]
    }
  ]
}
```

> **This policy JSON is pasted into the AWS Console when creating the IAM role
> (Step 1b above) — it does not go anywhere in the application code or repo.**
>
> Replace `<YOUR-ACCOUNT-ID>` with your 12-digit AWS account number when you
> paste the policy into AWS.  Find it at: AWS Console → top-right menu →
> your username → Account ID.  It never appears in any file you commit.
>
> **Why the account ID is required here:** the `us.anthropic.*` prefixed model ID
> is a **cross-region inference profile**, not a foundation model.  Inference
> profile ARNs are account-scoped (`inference-profile/`) whereas foundation model
> ARNs are AWS-global (`foundation-model/` with no account ID).  Using the wrong
> namespace causes a silent `AccessDeniedException`.

> Both `InvokeModel` and `InvokeModelWithResponseStream` are required.
> The Bedrock Converse API internally uses both actions even when you are
> not streaming — omitting `InvokeModelWithResponseStream` causes a 403.

4. Name the role (e.g. `tobi-bedrock-role`) and create it
5. Attach the role to your EC2 instance:
   - **During launch:** EC2 Console → Instance details → IAM instance profile
   - **After launch:** EC2 Console → Select instance → Actions → Security → Modify IAM role

**Enable IMDSv2** (security hardening — prevents any code on the instance from
stealing credentials without a token):

```bash
aws ec2 modify-instance-metadata-options \
  --instance-id <your-instance-id> \
  --http-tokens required \
  --region us-east-1
```

### 1c. Local development credentials

Choose one option:

**Option A — `aws configure` (recommended):**
```bash
pip install awscli
aws configure
# Prompts for: Access Key ID, Secret Access Key, Region, Output format
# Writes to ~/.aws/credentials — boto3 finds it automatically.
# docker-compose.bedrock.yml mounts ~/.aws into the container.
```

**Option B — Bedrock API keys** (new July 2025, no IAM user needed, 12-hour expiry):
```
AWS Console → Bedrock → API keys → Create API key
```
Use the generated key ID and secret as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
in your shell before running docker compose.

**Option C — Shell environment variables** (CI/CD or one-off testing):
```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1
docker compose -f docker-compose.yml -f docker-compose.bedrock.yml up
```

> Never put real credentials in `.env`, `docker-compose.yml`, or any committed file.

---

## Step 2 — Code Changes

Complete these sub-steps in order.  Each step is independently safe — the app
continues working after each one before you move to the next.

### 2a. Add boto3 to requirements.txt

Open `requirements.txt` and uncomment the boto3 line:

```
# Before:
# boto3>=1.34.0

# After:
boto3>=1.34.0
```

Rebuild the Docker image:
```bash
docker compose -f docker-compose.yml -f docker-compose.bedrock.yml build
```

Verify boto3 installed:
```bash
docker compose -f docker-compose.yml -f docker-compose.bedrock.yml run --rm app \
  python -c "import boto3; print(boto3.__version__)"
```

### 2b. Add new fields to `app/config.py`

Add these five fields to the `Settings` class, immediately after the `use_local_ai`
field (the comment block there marks the exact location):

```python
# Replaces USE_LOCAL_AI. Allowed values: "template" | "llama" | "bedrock"
ai_backend: str = "template"

# AWS Bedrock settings
aws_region: str = "us-east-1"
bedrock_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
# Cross-region inference profile routes to the best available US endpoint.
# Use "global.anthropic.claude-sonnet-4-5-20250929-v1:0" for global resilience.
```

> Do NOT add `aws_access_key_id` or `aws_secret_access_key` to Settings.
> boto3 handles credentials via its built-in credential chain — no code needed.

### 2c. Create the module-level boto3 client in `app/tobi_ai.py`

Add this block near the top of `tobi_ai.py`, after the existing imports:

```python
# ---------------------------------------------------------------------------
# boto3 client for AWS Bedrock (lazy — only created if boto3 is installed)
# ---------------------------------------------------------------------------
try:
    import boto3
    from botocore.config import Config as BotocoreConfig

    _bedrock_client = boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region,
        config=BotocoreConfig(
            retries={"mode": "adaptive", "max_attempts": 5}
            # "adaptive" = exponential backoff + jitter on ThrottlingException.
            # New AWS accounts default to 2-3 RPM for Claude — retries are essential.
        ),
    )
    _bedrock_available = True
except ImportError:
    _bedrock_client = None
    _bedrock_available = False
```

### 2d. Implement `get_bedrock_response_with_context()` in `app/tobi_ai.py`

The complete stub is already in `tobi_ai.py` as commented code (Mode 4 block).
Uncomment it and remove the `#` prefixes.  The function goes between
`get_ai_response_with_context` and `get_tobi_response_async`.

> **asyncio note:** The stub uses `asyncio.get_running_loop()` (already corrected
> in the stub).  Do **not** change it to `asyncio.get_event_loop()` — that API is
> deprecated since Python 3.10 and raises `RuntimeError` in Python 3.12+ when
> called inside a running event loop.

For reference, the key Bedrock-specific details:

```python
# Content blocks (Converse API requires a list, not a plain string):
"content": [{"text": msg.content}]   # ← not just msg.content

# System prompt is a TOP-LEVEL parameter, not inside messages[]:
system = [{"text": get_system_prompt(include_menu=True)}]

# The call:
response = _bedrock_client.converse(
    modelId=settings.bedrock_model_id,
    system=system,
    messages=messages,
    inferenceConfig={
        "maxTokens": 150,
        "temperature": 0.6,
        # Do NOT add topP alongside temperature — fails for Claude Sonnet 4.5+
        "stopSequences": ["\n\n", "Customer:", "User:"],
    },
)

# Response extraction:
ai_text = response["output"]["message"]["content"][0]["text"].strip()
```

### 2e. Add the dispatcher function to `app/tobi_ai.py`

Add this function directly above `get_ai_response_with_context`:

```python
async def get_response_with_context(prompt: str, session_id: str, db) -> str:
    """
    Dispatcher: routes to the correct AI backend based on settings.ai_backend.
    main.py calls this function; it never needs to know which backend is active.
    """
    if settings.ai_backend == "bedrock":
        return await get_bedrock_response_with_context(prompt, session_id, db)
    elif settings.ai_backend == "llama" or settings.llama_server_url:
        return await get_ai_response_with_context(prompt, session_id, db)
    else:
        return get_tobi_response(prompt)
```

### 2f. Update the one import in `app/main.py`

Change a single line:

```python
# Before:
from .tobi_ai import get_ai_response_with_context

# After:
from .tobi_ai import get_response_with_context
```

And update the call site in the `/chat` endpoint (same file):

```python
# Before:
ai_response = await get_ai_response_with_context(request.message, session.id, db)

# After:
ai_response = await get_response_with_context(request.message, session.id, db)
```

That is the only change needed in `main.py`.

---

## Step 3 — Docker

### Start in Bedrock mode

```bash
docker compose -f docker-compose.yml -f docker-compose.bedrock.yml up --build
```

The override file (`docker-compose.bedrock.yml`):
- Sets `AI_BACKEND=bedrock`
- Clears `depends_on` so the app does **not** wait for llama-server
- Reduces memory limits to 512 MB
- Mounts `~/.aws` for local dev credential discovery

> **Why `depends_on: {}`?**
> Without the explicit empty mapping, Docker Compose would inherit the base file's
> `depends_on: { llama-server: { condition: service_healthy } }` and block
> indefinitely — llama-server never starts in Bedrock mode.

### EC2 production deployment

On EC2 with an IAM role attached, no credentials are needed anywhere:

```bash
# Clone repo, pull latest
git clone https://github.com/Erics38/restaurant-ai-chatbot.git
cd restaurant-ai-chatbot
cp .env.example .env
# Edit .env: set AI_BACKEND=bedrock, AWS_REGION, BEDROCK_MODEL_ID, SECRET_KEY

docker compose -f docker-compose.yml -f docker-compose.bedrock.yml up -d --build
```

The container inherits the EC2 instance's IAM role via the metadata service.

---

## Step 4 — Testing

### Smoke test

```bash
# Health check
curl http://localhost:8000/health

# Chat with Bedrock
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What burgers do you have?"}'
```

**Expected:** A JSON response with Tobi's surfer-dude voice describing the House
Smash Burger with price.  If you get a template-style response instead, Bedrock
threw an error — check the logs.

### Verify which backend responded

```bash
docker compose logs app | grep -E "(Bedrock|llama-server|template fallback)"
```

The `get_bedrock_response_with_context` function logs:
```
INFO  Bedrock response (N msgs history, stop=end_turn, tokens=42): Oh dude...
```

If you see `Falling back to template responses`, Bedrock threw an exception —
the full error is logged on the line above it.

### Common errors

| Error | Cause | Fix |
|-------|-------|-----|
| `NoCredentialsError` | boto3 found no credentials | Run `aws configure`, check IAM role is attached, or set env vars |
| `AccessDeniedException` | IAM policy missing or wrong | Verify both `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` in policy |
| `ResourceNotFoundException` | Model ID not found in region | Check `BEDROCK_MODEL_ID` spelling; verify model access was approved in correct region |
| `ValidationException` | Bad request format | Usually `temperature` + `topP` both set — use only one |
| `ThrottlingException` | Rate limit hit | The adaptive retry config handles this automatically; also request a quota increase |
| Template responses silently returned | Bedrock exception caught, fallback triggered | Check `docker compose logs app` for the error above the fallback message |

---

## Step 5 — Production Checklist

Before pointing live traffic at the Bedrock backend:

- [ ] IAM role attached to EC2 instance (not key-based credentials)
- [ ] IMDSv2 required on the EC2 instance (`--http-tokens required`)
- [ ] `BEDROCK_MODEL_ID` pinned to a specific version ID (never use `latest`)
- [ ] Model access approved in the correct region
- [ ] Quota increase requested if expecting >3 requests/minute (new accounts default to 2–3 RPM)
- [ ] CloudWatch alarm created on `bedrock:InvokeModel` error rate
- [ ] AWS Cost Explorer dashboard bookmarked — charge is per input+output token
- [ ] `SECRET_KEY` set to a strong random value (`python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] `ENVIRONMENT=production` set (disables Swagger UI)
- [ ] `ALLOWED_ORIGINS` restricted to your domain

---

## Appendix: Converse API vs. invoke_model

The codebase uses the **Converse API**.  Here is why, and when you would use the other.

### Converse API (used here)

Model-agnostic.  The same request format works for Claude, Mistral, and Llama on
Bedrock.  System prompt is a first-class parameter.

```python
response = bedrock_client.converse(
    modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    system=[{"text": "You are Tobi..."}],
    messages=[
        {"role": "user", "content": [{"text": "What burgers do you have?"}]}
    ],
    inferenceConfig={"maxTokens": 150, "temperature": 0.6},
)
text = response["output"]["message"]["content"][0]["text"]
```

### invoke_model (not used here)

Model-specific JSON body.  For Claude, the body follows the Anthropic Messages API:

```python
import json
body = json.dumps({
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 150,
    "system": "You are Tobi...",
    "messages": [{"role": "user", "content": "What burgers do you have?"}],
})
response = bedrock_client.invoke_model(
    modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    body=body,
)
text = json.loads(response["body"].read())["content"][0]["text"]
```

**Use invoke_model when** you need features not yet available in Converse (e.g.,
certain vision or tool-use configurations) or when targeting a model that Converse
does not support.  For this chatbot, Converse is the right choice.
