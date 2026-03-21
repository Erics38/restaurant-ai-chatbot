#!/bin/bash

# verify-ci-locally.sh
# Run the same checks that GitHub Actions runs in CI
# This helps contributors verify their code before pushing

set -e  # Exit on any error

echo "🔍 Running CI checks locally..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Checking Code Formatting (Black)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if black --check app/ tests/ --line-length=120; then
    echo -e "${GREEN}✓ Black formatting check passed${NC}"
else
    echo -e "${RED}✗ Black formatting check failed${NC}"
    echo -e "${YELLOW}Fix with: black app/ tests/ --line-length=120${NC}"
    FAILURES=$((FAILURES + 1))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Running Linter (Flake8)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if flake8 app/ tests/ --max-line-length=120 --extend-ignore=E203,W503; then
    echo -e "${GREEN}✓ Flake8 linting passed${NC}"
else
    echo -e "${RED}✗ Flake8 linting failed${NC}"
    echo -e "${YELLOW}Review errors above and fix manually${NC}"
    FAILURES=$((FAILURES + 1))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  Checking Types (MyPy)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if mypy app/ --ignore-missing-imports; then
    echo -e "${GREEN}✓ MyPy type checking passed${NC}"
else
    echo -e "${RED}✗ MyPy type checking failed${NC}"
    echo -e "${YELLOW}Review errors above and fix type hints${NC}"
    FAILURES=$((FAILURES + 1))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  Running Unit Tests (Pytest)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if pytest tests/ -v --tb=short; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo -e "${YELLOW}Review test failures above${NC}"
    FAILURES=$((FAILURES + 1))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✓ All CI checks passed! You're ready to push.${NC}"
    exit 0
else
    echo -e "${RED}✗ $FAILURES check(s) failed. Fix errors above before pushing.${NC}"
    exit 1
fi
