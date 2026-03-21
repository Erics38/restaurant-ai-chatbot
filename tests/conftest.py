"""
Pytest configuration and shared fixtures.
"""

import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path so tests can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["USE_LOCAL_AI"] = "false"  # Use template mode for tests
    os.environ["LOG_LEVEL"] = "ERROR"  # Reduce log noise during tests
    yield
    # Cleanup after all tests


@pytest.fixture
def mock_session_id():
    """Provide a mock session ID for testing."""
    return "test-session-12345"


@pytest.fixture
def sample_order_items():
    """Provide sample order items for testing."""
    return [
        {"name": "House Smash Burger", "price": 16.00, "quantity": 2},
        {"name": "Truffle Fries", "price": 12.00, "quantity": 1},
    ]


@pytest.fixture
def sample_chat_messages():
    """Provide sample chat messages for testing."""
    return ["hello", "what burgers do you have?", "what do you recommend?", "how much does it cost?"]
