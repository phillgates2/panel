import os
import sys
import pathlib
os.environ['PANEL_USE_SQLITE'] = '1'
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from datetime import date
import uuid
from app import app, db, User

@pytest.fixture()
def client():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_admin_theme_protection(client):
    """Verify /admin/theme is protected: redirects for anonymous and non-admin users, accessible to system_admin."""
    with app.app_context():
        # create normal user with unique email
        u = User(first_name='Normal', last_name='User', email=f'user+{uuid.uuid4().hex[:8]}@example.com', dob=date(1990,1,1), role='user')
        u.set_password('x')
        db.session.add(u)
        # create admin user
        a = User(first_name='Admin', last_name='User', email=f'admin+{uuid.uuid4().hex[:8]}@example.com', dob=date(1970,1,1), role='system_admin')
        a.set_password('x')
        db.session.add(a)
        db.session.commit()

        # anonymous: should redirect to login
        r = client.get('/admin/theme', follow_redirects=False)
        assert r.status_code in (301, 302)
        assert '/login' in r.headers.get('Location', '')

        # logged in as normal user: redirected (to dashboard per app behavior)
        with client.session_transaction() as sess:
            sess['user_id'] = u.id
        r2 = client.get('/admin/theme', follow_redirects=False)
        assert r2.status_code in (301, 302)
        assert '/dashboard' in r2.headers.get('Location', '')

        # logged in as admin: should be allowed
        with client.session_transaction() as sess:
            sess['user_id'] = a.id
        r3 = client.get('/admin/theme')
        assert r3.status_code == 200
        assert b'Theme Editor' in r3.data
