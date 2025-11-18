import os

os.environ["PANEL_USE_SQLITE"] = "1"
import os

os.environ["PANEL_USE_SQLITE"] = "1"
import tempfile

import pytest

from app import app, db


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(prefix="panel_test_", suffix=".db")
    os.close(fd)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{path}"
    app.config["TESTING"] = True
    try:
        with app.app_context():
            try:
                db.engine.dispose()
            except Exception:
                pass
            db.create_all()
            yield app.test_client()
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()
        import os

        os.environ["PANEL_USE_SQLITE"] = "1"
        import tempfile
        from datetime import date

        import pytest

        from app import AuditLog, Server, User, app, db

        @pytest.fixture()
        def client():
            fd, path = tempfile.mkstemp(prefix="panel_test_", suffix=".db")
            os.close(fd)
            app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{path}"
            app.config["TESTING"] = True
            try:
                with app.app_context():
                    try:
                        db.engine.dispose()
                    except Exception:
                        pass
                    db.create_all()
                    yield app.test_client()
            finally:
                with app.app_context():
                    db.session.remove()
                    db.drop_all()
                try:
                    os.remove(path)
                except Exception:
                    pass

        def make_admin():
            u = User(
                first_name="Sys",
                last_name="Admin",
                email="sysadmin@example.com",
                dob=date(1990, 1, 1),
            )
            u.set_password("Password1!")
            u.role = "system_admin"
            db.session.add(u)
            db.session.commit()
            return u

        def test_create_and_export_audit(client):
            with app.app_context():
                admin = make_admin()

                # create a server record and an audit entry
                s = Server(name="ci-server", description="CI server")
                db.session.add(s)
                db.session.add(
                    AuditLog(actor_id=admin.id, action=f"create_server:{s.name}")
                )
                db.session.commit()

            # set session to be authenticated as admin and request export
            with client.session_transaction() as sess:
                sess["user_id"] = admin.id

            rv = client.get("/admin/audit/export")
            assert rv.status_code == 200
            data = rv.data.decode("utf-8")
            assert "id,timestamp,actor,action" in data
            assert f"create_server:{s.name}" in data
