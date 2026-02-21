import os
from urllib.parse import urlparse

from datetime import date

import pytest

from app import User, app, db


@pytest.fixture()
def client(request):
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        pytest.skip("Set DATABASE_URL to run tests (PostgreSQL-only)")
    if db_url.startswith("postgresql+psycopg2://"):
        db_url = "postgresql://" + db_url[len("postgresql+psycopg2://") :]
    if "test" not in (urlparse(db_url).path or "").lower():
        pytest.skip("DATABASE_URL must point to a test database")

    from app import create_app

    local_app = create_app()
    local_app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    local_app.config["TESTING"] = True
    request.module.app = local_app
    with local_app.app_context():
        db.create_all()
        yield local_app.test_client()
        db.session.remove()
        db.drop_all()


def test_register_and_login(client):
    with app.app_context():
        u = User(
            first_name="Test",
            last_name="User",
            email="t@example.com",
            dob=date(2000, 1, 1),
        )
        u.set_password("Password1!")
        db.session.add(u)
        db.session.commit()
        fetched = User.query.filter_by(email="t@example.com").first()
        assert fetched is not None
        assert fetched.check_password("Password1!")
