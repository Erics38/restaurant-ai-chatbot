# CI/CD Setup Guide

This document explains how the GitHub Actions CI/CD pipeline works and how to ensure it works for contributors.

## Overview

This project uses GitHub Actions for continuous integration and deployment. Every push and pull request automatically runs:

- ✅ Code formatting checks (Black)
- ✅ Linting (Flake8)
- ✅ Type checking (MyPy)
- ✅ Unit tests (Pytest) across Python 3.10, 3.11, 3.12
- ✅ Security scanning (CodeQL, Bandit)
- ✅ Docker builds

## For Repository Maintainers

### Current Workflows

Located in `.github/workflows/`:

1. **ci.yml** - Main CI pipeline (tests, linting, security)
2. **docker.yml** - Docker image builds and pushes
3. **release.yml** - Automated releases on version tags

### Workflow Triggers

```yaml
# ci.yml runs on:
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

# docker.yml runs on:
on:
  push:
    branches: [ main ]
    tags: [ 'v*.*.*' ]

# release.yml runs on:
on:
  push:
    tags: [ 'v*.*.*' ]
  workflow_dispatch:  # Manual trigger
```

### Secrets Required

The repository needs these secrets configured (Settings → Secrets and variables → Actions):

- `GITHUB_TOKEN` - Automatically provided by GitHub
- No additional secrets required for basic CI

Optional for enhanced features:
- `CODECOV_TOKEN` - For code coverage reporting (optional)
- `DOCKER_USERNAME` - For pushing to Docker Hub (optional)
- `DOCKER_PASSWORD` - For Docker Hub authentication (optional)

### Branch Protection Rules

Recommended settings for `main` branch (Settings → Branches):

1. ✅ Require pull request reviews before merging
2. ✅ Require status checks to pass before merging
   - Select: `test (3.10)`, `test (3.11)`, `test (3.12)`, `code-quality`, `security-check`
3. ✅ Require branches to be up to date before merging
4. ✅ Do not allow bypassing the above settings

## For Contributors

### Enabling Actions in Your Fork

1. **Fork the repository** on GitHub
2. Go to your fork's **Actions** tab
3. Click **"I understand my workflows, go ahead and enable them"**
4. Actions will now run on your pushes

### Viewing CI Results

**In Your Fork:**
```
https://github.com/YOUR_USERNAME/restaurant-ai-chatbot/actions
```

**In Pull Requests:**
- Scroll to the bottom of the PR page
- See all check statuses
- Click "Details" to view logs

### Local Development Workflow

```bash
# 1. Make changes to code

# 2. Run checks locally (same as CI)
black app/ tests/ --line-length=120
flake8 app/ tests/ --max-line-length=120 --extend-ignore=E203,W503
mypy app/ --ignore-missing-imports
pytest tests/ -v

# 3. Fix any issues

# 4. Commit and push
git add .
git commit -m "Your changes"
git push origin your-branch

# 5. Check Actions tab in your fork - CI runs automatically
```

### CI Status Badge

Add to your fork's README.md:

```markdown
![CI](https://github.com/YOUR_USERNAME/restaurant-ai-chatbot/workflows/CI%20-%20Test%20and%20Lint/badge.svg)
![Docker](https://github.com/YOUR_USERNAME/restaurant-ai-chatbot/workflows/Docker%20Build%20and%20Push/badge.svg)
```

## Troubleshooting CI Issues

### Tests Pass Locally But Fail in CI

**Line Endings Issue (Windows)**

```bash
# Configure git to use LF line endings
git config core.autocrlf input

# Convert existing files
dos2unix app/*.py tests/*.py

# Or let Black handle it
black app/ tests/ --line-length=120
```

**Python Version Differences**

CI tests on Python 3.10, 3.11, and 3.12. If tests pass locally but fail in CI:

```bash
# Test with multiple Python versions locally using tox
pip install tox
tox
```

### Docker Build Fails

```bash
# Test Docker build locally
docker build -t restaurant-ai:test .

# Test with docker-compose
docker-compose up --build
```

### Permission Denied Errors

Workflow files must have correct permissions. Check `.github/workflows/*.yml` permissions:

```yaml
permissions:
  contents: write  # For creating releases
  packages: write  # For pushing Docker images
  security-events: write  # For CodeQL
```

## Advanced: Running Workflows Manually

Some workflows support manual triggering:

1. Go to **Actions** tab
2. Select the workflow (e.g., "Release")
3. Click **"Run workflow"**
4. Select branch and click **"Run workflow"** button

## CI Pipeline Details

### Test Matrix Strategy

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
```

This runs tests on 3 Python versions in parallel, ensuring compatibility.

### Caching

CI uses caching to speed up builds:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: ${{ matrix.python-version }}
    cache: 'pip'  # Caches pip dependencies
```

### Artifact Storage

Test coverage reports are stored as artifacts:

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: coverage-report
    path: coverage.xml
```

Access artifacts:
1. Go to the workflow run
2. Scroll to "Artifacts" section
3. Download the reports

## Monitoring CI Health

### Check Run History

```bash
# Using GitHub CLI
gh run list --limit 20

# View specific run
gh run view RUN_ID

# Watch a running workflow
gh run watch
```

### Common Metrics to Monitor

- **Pass Rate**: Should be >95%
- **Build Time**: Should be <5 minutes
- **Flaky Tests**: Tests that fail inconsistently

## Updating CI Configuration

### Adding New Tests

1. Add test files to `tests/` directory
2. Pytest automatically discovers them
3. No workflow changes needed

### Adding New Python Version

Edit `.github/workflows/ci.yml`:

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12', '3.13']  # Add 3.13
```

### Adding New Linting Tools

Edit `.github/workflows/ci.yml`:

```yaml
- name: Install dependencies
  run: |
    pip install pytest black flake8 mypy
    pip install pylint  # Add new tool

- name: Run Pylint
  run: pylint app/
```

## Performance Optimization

### Speed Up CI Runs

1. **Use caching** (already implemented)
2. **Run jobs in parallel** (already implemented)
3. **Skip redundant workflows**:

```yaml
on:
  push:
    paths-ignore:
      - '**.md'
      - 'docs/**'
```

4. **Use workflow concurrency**:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

## Cost Considerations

GitHub Actions is **free** for public repositories!

For private repositories:
- **2,000 minutes/month** free
- Then **$0.008/minute** for Linux runners

Current usage:
- ~1-2 minutes per CI run
- ~100-200 minutes/month for active development

## Security Best Practices

1. ✅ **Never commit secrets** - Use GitHub Secrets
2. ✅ **Pin action versions** - Use `@v4` not `@main`
3. ✅ **Minimal permissions** - Only grant what's needed
4. ✅ **Review workflow changes** - Especially from external contributors
5. ✅ **Enable Dependabot** - Auto-update action versions

## Support and Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [Community Actions](https://github.com/marketplace?type=actions)

## Questions?

Check the [Contributing Guide](.github/CONTRIBUTING.md) or open an issue!
