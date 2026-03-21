"""
Test suite for Tobi AI chatbot functionality.
"""

import pytest
from app.tobi_ai import get_tobi_response, TOBI_RESPONSES
from app.menu_data import MENU_DATA


class TestTobiResponses:
    """Test Tobi's template response system."""

    def test_greeting_response(self):
        """Test Tobi responds to greetings."""
        greetings = ["hello", "hi", "hey", "what's up"]
        for greeting in greetings:
            response = get_tobi_response(greeting)
            assert isinstance(response, str)
            assert len(response) > 0
            # Tobi should give a friendly response
            assert len(response) > 5  # Basic validation

    def test_menu_question_response(self):
        """Test Tobi responds to menu questions."""
        menu_questions = ["what's on the menu", "show me the menu", "what do you have"]
        for question in menu_questions:
            response = get_tobi_response(question)
            assert isinstance(response, str)
            assert len(response) > 0

    def test_burger_question(self):
        """Test Tobi responds to burger-specific questions."""
        response = get_tobi_response("what burgers do you have?")
        assert isinstance(response, str)
        assert "burger" in response.lower()

    def test_starter_question(self):
        """Test Tobi responds to starter questions."""
        response = get_tobi_response("what starters do you have?")
        assert isinstance(response, str)
        assert len(response) > 0  # Just verify we get a response

    def test_drink_question(self):
        """Test Tobi responds to drink questions."""
        response = get_tobi_response("what drinks do you have?")
        assert isinstance(response, str)
        assert len(response) > 0  # Just verify we get a response

    def test_dessert_question(self):
        """Test Tobi responds to dessert questions."""
        response = get_tobi_response("what desserts do you have?")
        assert isinstance(response, str)
        assert len(response) > 0  # Just verify we get a response

    def test_recommendation_question(self):
        """Test Tobi gives recommendations."""
        response = get_tobi_response("what do you recommend?")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_price_question(self):
        """Test Tobi responds to price questions."""
        response = get_tobi_response("how much does it cost?")
        assert isinstance(response, str)
        assert "price" in response.lower() or "$" in response

    def test_random_message(self):
        """Test Tobi handles random messages."""
        response = get_tobi_response("random gibberish xyz123")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_empty_message_handled(self):
        """Test Tobi handles empty messages gracefully."""
        response = get_tobi_response("")
        assert isinstance(response, str)
        assert len(response) > 0


class TestTobiPersonality:
    """Test Tobi's surfer personality characteristics."""

    def test_uses_surfer_slang(self):
        """Test Tobi uses surfer slang in responses."""
        surfer_words = ["dude", "bro", "rad", "sick", "gnarly", "killer", "epic", "stoked", "totally", "yo"]
        responses = [get_tobi_response(msg) for msg in ["hello", "what's up", "yo"]]

        # At least one response should contain surfer slang
        found_slang = False
        for response in responses:
            if any(word in response.lower() for word in surfer_words):
                found_slang = True
                break

        assert found_slang, "Tobi should use surfer slang in responses"

    def test_friendly_tone(self):
        """Test Tobi maintains friendly tone."""
        response = get_tobi_response("hello")
        # Response should be positive and welcoming
        assert len(response) > 10
        assert not any(word in response.lower() for word in ["error", "wrong", "bad", "no"])


class TestMenuData:
    """Test menu data structure."""

    def test_menu_has_all_categories(self):
        """Test menu contains all required categories."""
        assert "starters" in MENU_DATA
        assert "mains" in MENU_DATA
        assert "desserts" in MENU_DATA
        assert "drinks" in MENU_DATA

    def test_menu_items_have_required_fields(self):
        """Test all menu items have name, description, and price."""
        # Skip restaurant_name which is just a string
        menu_categories = {k: v for k, v in MENU_DATA.items() if k != "restaurant_name"}

        for category_name, items in menu_categories.items():
            assert isinstance(items, list), f"{category_name} should be a list"
            for item in items:
                assert isinstance(item, dict), f"Item in {category_name} should be a dict"
                assert "name" in item, f"Item missing 'name' in {category_name}"
                assert "description" in item, f"Item missing 'description' in {category_name}"
                assert "price" in item, f"Item missing 'price' in {category_name}"
                assert isinstance(item["name"], str)
                assert isinstance(item["description"], str)
                assert isinstance(item["price"], (int, float))
                assert item["price"] > 0

    def test_menu_not_empty(self):
        """Test menu has items in each category."""
        assert len(MENU_DATA["starters"]) > 0
        assert len(MENU_DATA["mains"]) > 0
        assert len(MENU_DATA["desserts"]) > 0
        assert len(MENU_DATA["drinks"]) > 0


class TestTobiResponseTemplates:
    """Test Tobi's response template structure."""

    def test_greeting_templates_exist(self):
        """Test greeting templates are defined."""
        assert "greeting" in TOBI_RESPONSES
        assert isinstance(TOBI_RESPONSES["greeting"], list)
        assert len(TOBI_RESPONSES["greeting"]) > 0

    def test_default_templates_exist(self):
        """Test default templates are defined."""
        assert "default" in TOBI_RESPONSES
        assert isinstance(TOBI_RESPONSES["default"], list)
        assert len(TOBI_RESPONSES["default"]) > 0

    def test_all_templates_are_strings(self):
        """Test all response templates are strings."""
        for category, responses in TOBI_RESPONSES.items():
            for response in responses:
                assert isinstance(response, str)
                assert len(response) > 0


@pytest.mark.asyncio
class TestTobiAsyncFunctions:
    """Test async functionality (if implemented)."""

    async def test_async_response_imports(self):
        """Test async imports work correctly."""
        from app.tobi_ai import get_tobi_response_async

        assert callable(get_tobi_response_async)
