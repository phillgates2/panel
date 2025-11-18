import pytest

from app import create_app, db


@pytest.fixture
def app(tmp_path):
    dbfile = tmp_path / "test_panel.db"
    cfg = type('Cfg', (), {})()
    cfg.USE_SQLITE = True
    cfg.SQLALCHEMY_DATABASE_URI = f"sqlite:///{dbfile}"
    cfg.TESTING = True
    cfg.SECRET_KEY = 'test-secret'
    a = create_app(cfg)
    with a.app_context():
        db.create_all()
    yield a


@pytest.fixture
def client(app):
    return app.test_client()
