import os
os.environ['PANEL_USE_SQLITE'] = '1'
import pytest
from datetime import date
from app import app, db, User, Server, ServerUser, user_server_role, user_can_edit_server

@pytest.fixture()
def client(request):
    import tempfile
    fd, path = tempfile.mkstemp(prefix='panel_test_', suffix='.db')
    os.close(fd)
    try:
        from app import create_app
        local_app = create_app()
        local_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{path}'
        local_app.config['TESTING'] = True
        request.module.app = local_app
        try:
            with local_app.app_context():
                db.create_all()
                yield local_app.test_client()
        finally:
            with local_app.app_context():
                db.session.remove()
                db.drop_all()
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


def test_user_roles_and_server_assignment(client):
    with app.app_context():
        u1 = User(first_name='Admin', last_name='One', email='admin@example.com', dob=date(2000,1,1))
        u1.set_password('Password1!')
        u1.role = 'system_admin'
        db.session.add(u1)
        u2 = User(first_name='Mod', last_name='Two', email='mod@example.com', dob=date(2000,1,1))
        u2.set_password('Password1!')
        db.session.add(u2)
        s = Server(name='test-server', description='Test')
        db.session.add(s)
        db.session.commit()
        # assign u2 as server_mod
        su = ServerUser(server_id=s.id, user_id=u2.id, role='server_mod')
        db.session.add(su)
        db.session.commit()
        # role checks
        assert user_server_role(u1, s) == 'system_admin'
        assert user_server_role(u2, s) == 'server_mod'
        assert user_can_edit_server(u1, s) is True
        assert user_can_edit_server(u2, s) is True
