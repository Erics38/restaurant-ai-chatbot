"""
Test suite for Pydantic data models.
"""

import pytest
from pydantic import ValidationError
from app.models import ChatRequest, ChatResponse


class TestChatRequest:
    """Test ChatRequest model."""

    def test_valid_chat_request(self):
        """Test creating a valid chat request."""
        msg = ChatRequest(message="Hello, Tobi!")
        assert msg.message == "Hello, Tobi!"

    def test_empty_message_rejected(self):
        """Test empty message is rejected."""
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_whitespace_message_trimmed(self):
        """Test whitespace messages are handled."""
        # Note: Pydantic may trim whitespace but allow it
        # This test verifies the model accepts input gracefully
        msg = ChatRequest(message="hello   ")
        assert isinstance(msg.message, str)


class TestChatResponse:
    """Test ChatResponse model."""

    def test_valid_chat_response(self):
        """Test creating a valid chat response."""
        response = ChatResponse(
            response="Hey dude!", session_id="abc123", has_magic_password=False, restaurant="The Common House"
        )
        assert response.response == "Hey dude!"
        assert response.session_id == "abc123"
        assert response.has_magic_password is False
        assert response.restaurant == "The Common House"

    def test_magic_password_default_false(self):
        """Test has_magic_password defaults to False."""
        response = ChatResponse(response="Hey!", session_id="abc", restaurant="Test Restaurant")
        assert response.has_magic_password is False


class TestModelIntegration:
    """Test model integration and type safety."""

    def test_model_to_dict_conversion(self):
        """Test models can be converted to dictionaries."""
        msg = ChatRequest(message="Test")
        msg_dict = msg.model_dump()
        assert isinstance(msg_dict, dict)
        assert msg_dict["message"] == "Test"

    def test_model_json_serialization(self):
        """Test models can be serialized to JSON."""
        response = ChatResponse(response="Test", session_id="123", restaurant="Test Restaurant")
        json_str = response.model_dump_json()
        assert isinstance(json_str, str)
        assert "Test" in json_str
