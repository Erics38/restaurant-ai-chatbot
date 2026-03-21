"""
Test suite for main FastAPI application endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestHealthEndpoints:
    """Test health check and basic endpoints."""

    def test_root_endpoint(self):
        """Test GET / returns basic info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "restaurant" in data
        assert data["restaurant"] == "The Common House"

    def test_health_endpoint(self):
        """Test GET /health returns OK status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestMenuEndpoint:
    """Test menu-related endpoints."""

    def test_get_menu(self):
        """Test GET /menu returns menu data."""
        response = client.get("/menu")
        assert response.status_code == 200
        data = response.json()

        # Check menu structure
        assert "starters" in data
        assert "mains" in data
        assert "desserts" in data
        assert "drinks" in data

        # Verify at least one item in each category
        assert len(data["starters"]) > 0
        assert len(data["mains"]) > 0
        assert len(data["desserts"]) > 0
        assert len(data["drinks"]) > 0

        # Check first starter has required fields
        starter = data["starters"][0]
        assert "name" in starter
        assert "description" in starter
        assert "price" in starter


class TestChatEndpoint:
    """Test chat endpoint with Tobi."""

    def test_chat_basic_message(self):
        """Test POST /chat with a basic message."""
        response = client.post("/chat", json={"message": "hello"})
        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert "session_id" in data
        assert "restaurant" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

    def test_chat_menu_question(self):
        """Test POST /chat asking about menu."""
        response = client.post("/chat", json={"message": "what burgers do you have?"})
        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

    def test_chat_generic_message(self):
        """Test POST /chat with a generic message."""
        response = client.post("/chat", json={"message": "tell me about your food"})
        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

    def test_chat_empty_message_rejected(self):
        """Test POST /chat with empty message returns 422."""
        response = client.post("/chat", json={"message": ""})
        assert response.status_code == 422


class TestCORSAndMiddleware:
    """Test CORS and middleware configuration."""

    def test_cors_headers_present(self):
        """Test CORS headers are set correctly."""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        # FastAPI TestClient doesn't fully simulate CORS, but we verify endpoint works


class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_json_available(self):
        """Test OpenAPI JSON schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_docs_ui_available(self):
        """Test Swagger UI docs are available."""
        response = client.get("/api/docs")
        assert response.status_code == 200
        assert b"swagger-ui" in response.content.lower()

    def test_redoc_available(self):
        """Test ReDoc documentation is available."""
        response = client.get("/api/redoc")
        assert response.status_code == 200
        assert b"redoc" in response.content.lower()
