# CI/CD Pipeline Documentation

Complete guide to the automated CI/CD pipeline for Restaurant AI.

---

## Overview

The CI/CD pipeline automates testing, security scanning, Docker builds, and deployments using GitHub Actions.

### What Gets Automated

- Code quality checks (linting, formatting)
- Unit and integration tests
- Security vulnerability scanning
- Docker image builds and publishing
- Dependency updates
- Code analysis

---

## GitHub Actions Workflows

### 1. CI Workflow (ci.yml)

**Triggers**: Push to main/develop, Pull Requests

**Jobs**:

#### Test Job
- Runs on: Python 3.10, 3.11, 3.12
- Steps:
  1. Code checkout
  2. Python setup with pip caching
  3. Install dependencies
  4. Black (code formatting check)
  5. Flake8 (linting)
  6. MyPy (type checking)
  7. Pytest (unit tests with coverage)
  8. Upload coverage to Codecov

#### Security Check Job
- Runs on: Python 3.11
- Steps:
  1. Safety check (known vulnerabilities)
  2. Bandit (security linter)
  3. Upload security reports

#### Code Quality Job
- Runs on: Ubuntu latest
- Steps:
  1. CodeQL analysis (GitHub security)
  2. Detect security vulnerabilities

**Status Badge**:
```markdown
![CI Status](https://github.com/Erics38/Tobi-the-local-server-serving-server/actions/workflows/ci.yml/badge.svg)
```

---

### 2. Docker Workflow (docker.yml)

**Triggers**: Push to main, version tags (v*), Pull Requests

**Jobs**:

#### Build and Push Job
- Builds multi-platform Docker images (amd64, arm64)
- Pushes to GitHub Container Registry (ghcr.io)
- Uses Docker layer caching for faster builds
- Runs Trivy vulnerability scanner
- Uploads security results to GitHub Security tab

**Image Tags**:
- `latest` - Latest main branch
- `v1.0.0` - Semantic version tags
- `main-abc123` - Branch + commit SHA
- `pr-123` - Pull request number

**Pull Images**:
```bash
docker pull ghcr.io/erics38/tobi-the-local-server-serving-server:latest
```

**Status Badge**:
```markdown
![Docker Build](https://github.com/Erics38/Tobi-the-local-server-serving-server/actions/workflows/docker.yml/badge.svg)
```

---

### 3. Dependabot (dependabot.yml)

**Schedule**: Weekly (Mondays)

**Updates**:
- Python dependencies (requirements.txt)
- Docker base images (Dockerfile)
- GitHub Actions versions

**Configuration**:
- Max 10 PRs for Python deps
- Max 5 PRs for Docker/Actions
- Auto-assigns to @Erics38
- Auto-labels PRs

**How It Works**:
1. Dependabot scans dependencies weekly
2. Creates PR for each update
3. CI runs automatically on PR
4. Review and merge if tests pass

---

## Setting Up CI/CD

### Step 1: Enable GitHub Actions

Already enabled when you push .github/workflows/ files!

### Step 2: Configure Secrets (Optional)

For advanced features, add secrets in GitHub Settings > Secrets:

```
Settings > Secrets and variables > Actions > New repository secret
```

**Optional Secrets**:
- `CODECOV_TOKEN` - For code coverage reports
- `DOCKER_HUB_USERNAME` - If using Docker Hub
- `DOCKER_HUB_TOKEN` - If using Docker Hub

### Step 3: Enable Dependabot

Already enabled with .github/dependabot.yml!

Check: Settings > Code security and analysis > Dependabot

---

## Workflow Status

View workflow runs:
```
https://github.com/Erics38/Tobi-the-local-server-serving-server/actions
```

### Check Status

**All Workflows**:
- Go to: https://github.com/Erics38/Tobi-the-local-server-serving-server/actions

**Specific Workflow**:
- CI: Click "CI - Test and Lint" tab
- Docker: Click "Docker Build and Push" tab

**On Pull Requests**:
- Status checks appear at bottom of PR
- Green checkmark = passed
- Red X = failed
- Click "Details" to see logs

---

## Using CI/CD in Development

### Before Pushing Code

**Run checks locally**:
```bash
# Format code
black app/

# Lint
flake8 app/ --max-line-length=120

# Type check
mypy app/ --ignore-missing-imports

# Run tests
pytest tests/ -v
```

### Creating a Pull Request

1. Push your branch:
   ```bash
   git checkout -b feature/my-feature
   git push origin feature/my-feature
   ```

2. Create PR on GitHub
3. CI runs automatically
4. Wait for green checkmarks
5. Address any failures
6. Merge when all checks pass

### Fixing Failed Checks

**Black formatting failed**:
```bash
black app/
git add .
git commit -m "fix: Apply black formatting"
git push
```

**Flake8 linting failed**:
```bash
# Fix issues shown in logs
flake8 app/ --max-line-length=120
# Fix and commit
```

**Tests failed**:
```bash
# Run tests locally
pytest tests/ -v
# Fix failing tests
# Commit and push
```

---

## Docker Image Usage

### Pull Published Images

```bash
# Latest version
docker pull ghcr.io/erics38/tobi-the-local-server-serving-server:latest

# Specific version
docker pull ghcr.io/erics38/tobi-the-local-server-serving-server:v1.0.0

# Run it
docker run -p 8000:8000 ghcr.io/erics38/tobi-the-local-server-serving-server:latest
```

### In docker-compose.yml

```yaml
services:
  app:
    image: ghcr.io/erics38/tobi-the-local-server-serving-server:latest
    # ... rest of config
```

---

## Release Process

### Creating a Release

1. **Update version** (if using semver):
   ```bash
   # Update version in relevant files
   git add .
   git commit -m "chore: Bump version to 1.0.0"
   git push
   ```

2. **Create and push tag**:
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

3. **Automated actions**:
   - Docker workflow builds image
   - Tags as v1.0.0, v1.0, v1, latest
   - Pushes to GitHub Container Registry

4. **Create GitHub Release** (optional):
   - Go to Releases > Create new release
   - Select tag v1.0.0
   - Add release notes
   - Publish

---

## Monitoring CI/CD

### Build Status

Add badges to README.md:

```markdown
![CI Status](https://github.com/Erics38/Tobi-the-local-server-serving-server/actions/workflows/ci.yml/badge.svg)
![Docker Build](https://github.com/Erics38/Tobi-the-local-server-serving-server/actions/workflows/docker.yml/badge.svg)
```

### Email Notifications

GitHub sends emails for:
- Failed workflow runs
- Dependabot PRs
- Security alerts

Configure: Settings > Notifications

### Slack/Discord Integration (Optional)

Use GitHub Actions marketplace:
- slack-notify action
- discord-webhook action

---

## Troubleshooting

### Workflow Failed - "Error: Process completed with exit code 1"

**Solution**: Click "Details" to see full logs, check which step failed

### Docker Build Out of Disk Space

**Solution**: GitHub runners have limited space, optimize Dockerfile

### Dependabot PR Failed Tests

**Solution**: Review breaking changes, update code to be compatible

### Can't Push Docker Image - Permission Denied

**Solution**: Check GitHub Package permissions:
- Settings > Packages
- Ensure write permission enabled

---

## Best Practices

### 1. Keep Workflows Fast
- Use caching (pip, Docker layers)
- Run tests in parallel
- Current build time: ~3-5 minutes

### 2. Don't Ignore Failures
- Fix broken builds immediately
- Don't merge PRs with failing checks
- Treat warnings seriously

### 3. Keep Dependencies Updated
- Review Dependabot PRs weekly
- Test updates before merging
- Read changelogs for breaking changes

### 4. Security First
- Never commit secrets to code
- Use GitHub Secrets for sensitive data
- Review security scan results

### 5. Test Locally First
- Run linters before pushing
- Run tests before creating PR
- Use pre-commit hooks (optional)

---

## Advanced: Pre-commit Hooks (Optional)

Install pre-commit to run checks before each commit:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black

  - repo: https://github.com/PyCQA/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
EOF

# Install hooks
pre-commit install
```

Now checks run automatically on `git commit`!

---

## CI/CD Architecture

```
┌─────────────────┐
│   Developer     │
│   git push      │
└────────┬────────┘
         │
         v
┌─────────────────────┐
│  GitHub Actions     │
│  ┌───────────────┐  │
│  │ CI Workflow   │  │ ← Lint, Test, Type Check
│  ├───────────────┤  │
│  │ Docker Build  │  │ ← Build & Push Image
│  ├───────────────┤  │
│  │ Security Scan │  │ ← Vulnerability Check
│  └───────────────┘  │
└─────────┬───────────┘
          │
          v
┌─────────────────────┐
│ GitHub Container    │
│ Registry (ghcr.io)  │ ← Published Docker Images
└─────────────────────┘
          │
          v
┌─────────────────────┐
│   Deployment        │
│ (Pull & Run Image)  │ ← Production Server
└─────────────────────┘
```

---

## Cost

GitHub Actions is **FREE** for public repositories!

Included:
- Unlimited workflow minutes
- 2,000 GitHub Actions minutes/month (private repos)
- 500MB GitHub Packages storage (free)
- All workflows and Dependabot

---

## Next Steps

1. **Add Status Badges** to README.md
2. **Set up Codecov** for coverage tracking (optional)
3. **Configure Notifications** in GitHub settings
4. **Create release workflow** for automated releases (optional)
5. **Add deployment workflow** for production (coming soon)

---

## Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Dependabot Docs](https://docs.github.com/en/code-security/dependabot)
- [Docker GitHub Actions](https://github.com/docker/build-push-action)
- [CodeQL Analysis](https://codeql.github.com/)

---

**Your CI/CD pipeline is ready to use! Push code and watch it work automatically.**
