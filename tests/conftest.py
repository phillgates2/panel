import json
import os
import warnings
from datetime import date
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SAWarning

from app import create_app, db
from src.panel.models import User


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
        # Prevent attribute expiration so fixtures remain usable outside session
        db.session.expire_on_commit = False
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
        dob="1990-01-01",
    )
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture
def system_admin(app):
    ctx = app.app_context()
    ctx.push()
    u = User(
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        dob=date(2000, 1, 1),
        role="system_admin",
    )
    u.set_password("password")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def regular_user(app):
    ctx = app.app_context()
    ctx.push()
    u = User(
        first_name="Regular",
        last_name="User",
        email="regular@example.com",
        dob=date(2000, 1, 1),
        role="user",
    )
    u.set_password("password")
    db.session.add(u)
    db.session.commit()
    return u


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
        "dob": "1990-01-01",
    }


@pytest.fixture
def sample_login_data():
    """Sample login data for testing."""
    return {"email": "test@example.com", "password": "Password123!"}


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
    config.addinivalue_line(
        "markers",
        "e2e: browser/UI end-to-end tests (deselected by default; set RUN_E2E=1 to run)",
    )

    # Suppress noisy SQLAlchemy identity-map warnings that are benign in tests
    warnings.filterwarnings(
        "ignore",
        category=SAWarning,
        message="Identity map already had an identity for",
    )


def pytest_collection_modifyitems(config, items):
    """Deselect end-to-end/UI tests by default.

    These tests require external browser tooling (Playwright/Selenium + drivers)
    and are typically not runnable in minimal dev containers.

    Set RUN_E2E=1 to include them.
    """

    run_e2e = os.environ.get("RUN_E2E", "").lower() in ("1", "true", "yes")
    if run_e2e:
        return

    deselected = []
    selected = []
    for item in items:
        if "e2e" in item.keywords:
            deselected.append(item)
        else:
            selected.append(item)

    if deselected:
        items[:] = selected
        config.hook.pytest_deselected(items=deselected)


# Test data helpers
def create_test_user(db_session, **kwargs):
    """Helper function to create a test user."""
    defaults = {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "dob": "1990-01-01",
    }
    defaults.update(kwargs)

    user = User(**defaults)
    db_session.session.add(user)
    db_session.session.commit()
    return user


def login_test_user(client, email="test@example.com", password="Password123!"):
    """Helper function to login a test user."""
    response = client.post(
        "/login",
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
    )
    if response.status_code == 200:
        data = json.loads(response.data)
        return data.get("access_token")
    return None


def make_authenticated_request(client, method, url, token, **kwargs):
    """Helper function to make authenticated requests."""
    headers = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    kwargs["headers"] = headers
    return getattr(client, method.lower())(url, **kwargs)
