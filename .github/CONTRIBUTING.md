# Contributing to Restaurant AI Chatbot

Thanks for your interest in contributing! This document explains how to set up your development environment and ensure your contributions pass all CI checks.

## Quick Start for Contributors

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/restaurant-ai-chatbot.git
cd restaurant-ai-chatbot
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov black flake8 mypy
```

### 3. Verify Setup Works

```bash
# Run tests locally
pytest tests/ -v

# Check code formatting
black --check app/ tests/ --line-length=120

# Run linter
flake8 app/ tests/ --max-line-length=120 --extend-ignore=E203,W503

# Check types
mypy app/ --ignore-missing-imports
```

All of these should pass before you commit!

## GitHub Actions CI/CD

### What Runs Automatically

Every time you push code or create a pull request, GitHub Actions automatically runs:

1. **Code Quality Checks**
   - Black (code formatting)
   - Flake8 (linting)
   - MyPy (type checking)
   - CodeQL (security analysis)

2. **Tests**
   - All unit tests across Python 3.10, 3.11, 3.12
   - Code coverage reporting

3. **Security Scans**
   - Bandit (security linting)
   - Safety (dependency vulnerabilities)

4. **Docker Builds**
   - Ensures Docker images build successfully

### Checking CI Status

**Web**: Go to the "Actions" tab in your forked repository
**CLI**: `gh run list` (if you have GitHub CLI installed)

### CI Badge for Your Fork

Add this to your fork's README to show CI status:

```markdown
![CI Status](https://github.com/YOUR_USERNAME/restaurant-ai-chatbot/workflows/CI%20-%20Test%20and%20Lint/badge.svg)
```

## Pre-Commit Checks (Recommended)

Run these before every commit to catch issues early:

```bash
# Quick check script
black app/ tests/ --line-length=120
flake8 app/ tests/ --max-line-length=120 --extend-ignore=E203,W503
pytest tests/ -v
```

### Optional: Automate Pre-Commit Checks

Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

Create `.pre-commit-config.yaml` in the repo root:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        args: [--line-length=120]

  - repo: https://github.com/PyCQA/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120, --extend-ignore=E203,W503]
```

## Common CI Failures and Fixes

### Black Formatting Errors

```bash
# Fix automatically
black app/ tests/ --line-length=120
```

### Flake8 Linting Errors

```bash
# See errors
flake8 app/ tests/ --max-line-length=120 --extend-ignore=E203,W503

# Fix manually or use autopep8
pip install autopep8
autopep8 --in-place --aggressive --aggressive app/
```

### Test Failures

```bash
# Run tests with detailed output
pytest tests/ -v --tb=short

# Run specific test
pytest tests/test_main.py::TestChatEndpoint::test_chat_basic_message -v
```

### Line Ending Issues (Windows)

If you see "would reformat" errors in CI but not locally:

```bash
# Convert CRLF to LF (Windows users)
git config core.autocrlf input

# Or use dos2unix
dos2unix app/*.py tests/*.py
```

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and commit**
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

3. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create Pull Request**
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your fork and branch
   - Fill out the PR template

5. **Wait for CI checks**
   - All checks must pass before merge
   - Address any CI failures by pushing new commits

## Running Tests Locally

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_main.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=app --cov-report=html
# View coverage report at htmlcov/index.html
```

### Run in Watch Mode (for development)

```bash
pip install pytest-watch
ptw tests/
```

## Code Style Guidelines

- **Line length**: 120 characters max
- **Formatting**: Use Black formatter
- **Docstrings**: Required for all public functions/classes
- **Type hints**: Encouraged but not required
- **Comments**: Explain "why", not "what"

## Questions?

- Check existing issues and pull requests
- Ask in GitHub Discussions
- Read the [README](../README.md) and [SETUP](../SETUP.md)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
