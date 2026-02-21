"""API Integration Tests"""

import json

from app import db
from src.panel.models import User


def test_health_endpoints_integration(client):
    """Test health endpoints return expected structure."""
    response = client.get("/health")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert "status" in data
    assert "timestamp" in data


def test_openapi_spec_endpoint(client):
    """Test OpenAPI specification endpoint (optional)."""
    response = client.get("/api/openapi.json")
    if response.status_code == 200:
        data = json.loads(response.data)
        assert "openapi" in data


def test_error_handling_integration(client):
    """Test 404 error handling."""
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404


def test_basic_app_creation(app):
    """Test that the app fixture can be created successfully."""
    assert app is not None
    assert hasattr(app, "config")


def test_database_connection(db_session):
    """Test DB connection works."""
    result = db.session.execute(db.text("SELECT 1")).scalar()
    assert result == 1


def test_user_model_creation(db_session):
    """Test basic user model creation."""
    user = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password_hash="hashed_password",
        dob="1990-01-01",
    )

    db.session.add(user)
    db.session.commit()

    retrieved_user = User.query.filter_by(email="test@example.com").first()
    assert retrieved_user is not None
    assert retrieved_user.first_name == "Test"
    assert retrieved_user.email == "test@example.com"


def test_database_connection_pooling(db_session):
    """Test basic pooling / repeated queries."""
    for _ in range(5):
        result = db.session.execute(db.text("SELECT 1")).scalar()
        assert result == 1
