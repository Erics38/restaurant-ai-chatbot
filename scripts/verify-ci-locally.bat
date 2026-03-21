@echo off
REM verify-ci-locally.bat
REM Windows version - Run the same checks that GitHub Actions runs in CI

echo.
echo ================================================
echo   Running CI Checks Locally
echo ================================================
echo.

set FAILURES=0

REM Check if in correct directory
if not exist "app\" (
    echo Error: Run this script from the repository root
    exit /b 1
)

echo ================================================
echo 1. Checking Code Formatting (Black)
echo ================================================
echo.

black --check app\ tests\ --line-length=120
if %errorlevel% neq 0 (
    echo [FAILED] Black formatting check failed
    echo Fix with: black app\ tests\ --line-length=120
    set /a FAILURES+=1
) else (
    echo [PASSED] Black formatting check passed
)

echo.
echo ================================================
echo 2. Running Linter (Flake8)
echo ================================================
echo.

flake8 app\ tests\ --max-line-length=120 --extend-ignore=E203,W503
if %errorlevel% neq 0 (
    echo [FAILED] Flake8 linting failed
    set /a FAILURES+=1
) else (
    echo [PASSED] Flake8 linting passed
)

echo.
echo ================================================
echo 3. Checking Types (MyPy)
echo ================================================
echo.

mypy app\ --ignore-missing-imports
if %errorlevel% neq 0 (
    echo [FAILED] MyPy type checking failed
    set /a FAILURES+=1
) else (
    echo [PASSED] MyPy type checking passed
)

echo.
echo ================================================
echo 4. Running Unit Tests (Pytest)
echo ================================================
echo.

pytest tests\ -v --tb=short
if %errorlevel% neq 0 (
    echo [FAILED] Some tests failed
    set /a FAILURES+=1
) else (
    echo [PASSED] All tests passed
)

echo.
echo ================================================
echo Summary
echo ================================================
echo.

if %FAILURES% equ 0 (
    echo [SUCCESS] All CI checks passed! You're ready to push.
    exit /b 0
) else (
    echo [FAILED] %FAILURES% check(s) failed. Fix errors above before pushing.
    exit /b 1
)
