import os
os.environ['PANEL_USE_SQLITE'] = '1'
from datetime import date
import pytest
from app import app, db, User, Server, ServerUser, AuditLog

@pytest.fixture()
def client():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def make_admin():
    u = User(first_name='Sys', last_name='Admin', email='sysadmin@example.com', dob=date(1990,1,1))
    u.set_password('Password1!')
    u.role = 'system_admin'
    db.session.add(u)
    db.session.commit()
    return u


def test_create_and_delete_server_and_audit_export(client):
    with app.app_context():
        admin = make_admin()
        # set session
        c = client
        with c.session_transaction() as sess:
            sess['user_id'] = admin.id
            sess['csrf_token'] = 'test-token'
        # create server
        rv = c.post('/admin/servers/create', data={'name': 'ci-server', 'description': 'CI', 'csrf_token': 'test-token'}, follow_redirects=True)
        assert rv.status_code == 200
        s = Server.query.filter_by(name='ci-server').first()
        assert s is not None
        # check server user mapping (admin assigned)
        su = ServerUser.query.filter_by(server_id=s.id, user_id=admin.id).first()
        assert su is not None and su.role == 'server_admin'
        # check audit log entry exists
        al = AuditLog.query.filter(AuditLog.action.contains('create_server:ci-server')).first()
        assert al is not None
        # export audit CSV
        rv = c.get('/admin/audit/export')
        assert rv.status_code == 200
        data = rv.data.decode('utf-8')
        assert 'id,timestamp,actor,action' in data
        assert 'create_server:ci-server' in data
        # delete server
        with c.session_transaction() as sess:
            sess['user_id'] = admin.id
            sess['csrf_token'] = 'test-token'
        rv = c.post(f'/admin/servers/{s.id}/delete', data={'csrf_token': 'test-token'}, follow_redirects=True)
        assert rv.status_code == 200
        s2 = Server.query.filter_by(name='ci-server').first()
        assert s2 is None
        al2 = AuditLog.query.filter(AuditLog.action.contains('delete_server:ci-server')).first()
        assert al2 is not None
