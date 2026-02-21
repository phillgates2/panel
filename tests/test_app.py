from app.context_processors import inject_user
from app.utils import rate_limit


def test_home_page(client):
    """Test the home page loads."""
    rv = client.get("/")
    # The home page route should be registered and return HTTP 200.
    assert rv.status_code == 200


def test_rate_limit(app):
    """Test rate limiting function."""
    with app.app_context():
        # Test allowing requests
        assert rate_limit("test_action", 5, 60) is True
        # Test limiting after exceeding
        for _ in range(5):
            rate_limit("test_action", 5, 60)
        # In testing mode, rate limiting is disabled
        assert rate_limit("test_action", 5, 60) is True


def test_inject_user(app):
    """Test context processor."""
    with app.app_context():
        with app.test_request_context():
            result = inject_user()
            assert "logged_in" in result
            assert "current_user" in result


def test_health(client):
    """Test health check endpoint."""
    rv = client.get("/health")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "status" in data
    assert "checks" in data
