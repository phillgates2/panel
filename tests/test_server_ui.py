from datetime import date

from app import db
from src.panel.models import AuditLog, Server, User


def test_create_and_export_audit(client, app):
    with app.app_context():
        admin = User(
            first_name="Sys",
            last_name="Admin",
            email="sysadmin@example.com",
            dob=date(1990, 1, 1),
            role="system_admin",
        )
        admin.set_password("Password1!")
        db.session.add(admin)
        db.session.commit()

        server = Server(name="ci-server", description="CI server")
        db.session.add(server)
        db.session.flush()

        db.session.add(AuditLog(actor_id=admin.id, action=f"create_server:{server.name}"))
        db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = admin.id

    rv = client.get("/admin/audit/export")
    assert rv.status_code == 200
    data = rv.data.decode("utf-8")
    assert "id,timestamp,actor,action" in data
    assert f"create_server:{server.name}" in data
