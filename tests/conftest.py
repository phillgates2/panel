import pytest
import json
from unittest.mock import Mock

from app import create_app, db
from models import User


@pytest.fixture
def app(tmp_path):
    dbfile = tmp_path / "test_panel.db"
    cfg = type("Cfg", (), {})()
    cfg.USE_SQLITE = True
    cfg.SQLALCHEMY_DATABASE_URI = f"sqlite:///{dbfile}"
    cfg.TESTING = True
    cfg.SECRET_KEY = "test-secret"
    a = create_app(cfg)
    with a.app_context():
        db.create_all()
    yield a


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def db_session(app):
    """Create a database session for testing."""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password_hash="hashed_password",
        dob="1990-01-01"
    )
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for a test user."""
    # This would need to be implemented based on your auth system
    # For now, return empty headers
    return {}


@pytest.fixture
def mock_cache():
    """Mock cache for testing."""
    cache = Mock()
    cache.get.return_value = None
    cache.set.return_value = True
    cache.delete.return_value = True
    return cache


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis = Mock()
    redis.get.return_value = None
    redis.set.return_value = True
    redis.delete.return_value = True
    redis.exists.return_value = False
    return redis


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
        "dob": "1990-01-01"
    }


@pytest.fixture
def sample_login_data():
    """Sample login data for testing."""
    return {
        "email": "test@example.com",
        "password": "Password123!"
    }


@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock external services for testing."""
    with pytest.MonkeyPatch().context() as m:
        # Mock any external API calls or services
        yield m


# Custom markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "unit: mark test as unit test")


# Test data helpers
def create_test_user(db_session, **kwargs):
    """Helper function to create a test user."""
    defaults = {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "dob": "1990-01-01"
    }
    defaults.update(kwargs)

    user = User(**defaults)
    db_session.session.add(user)
    db_session.session.commit()
    return user


def login_test_user(client, email="test@example.com", password="Password123!"):
    """Helper function to login a test user."""
    response = client.post('/login',
                          data=json.dumps({"email": email, "password": password}),
                          content_type='application/json')
    if response.status_code == 200:
        data = json.loads(response.data)
        return data.get('access_token')
    return None


def make_authenticated_request(client, method, url, token, **kwargs):
    """Helper function to make authenticated requests."""
    headers = kwargs.get('headers', {})
    headers['Authorization'] = f'Bearer {token}'
    kwargs['headers'] = headers
    return getattr(client, method.lower())(url, **kwargs)
