import os
from urllib.parse import urlparse

from datetime import date

import pytest

from app import (Server, ServerUser, User, app, db, user_can_edit_server,
                 user_server_role)


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


def test_user_roles_and_server_assignment(client):
    with app.app_context():
        u1 = User(
            first_name="Admin",
            last_name="One",
            email="admin@example.com",
            dob=date(2000, 1, 1),
        )
        u1.set_password("Password1!")
        u1.role = "system_admin"
        db.session.add(u1)
        u2 = User(
            first_name="Mod",
            last_name="Two",
            email="mod@example.com",
            dob=date(2000, 1, 1),
        )
        u2.set_password("Password1!")
        db.session.add(u2)
        s = Server(name="test-server", description="Test")
        db.session.add(s)
        db.session.commit()
        # assign u2 as server_mod
        su = ServerUser(server_id=s.id, user_id=u2.id, role="server_mod")
        db.session.add(su)
        db.session.commit()
        # role checks
        assert user_server_role(u1, s) == "system_admin"
        assert user_server_role(u2, s) == "server_mod"
        assert user_can_edit_server(u1, s) is True
        assert user_can_edit_server(u2, s) is True
