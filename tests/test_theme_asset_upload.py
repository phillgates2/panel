import os
import sys
import pathlib
import io
import base64
os.environ['PANEL_USE_SQLITE'] = '1'
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
import tempfile
import os
from datetime import date
from app import app, db, User, SiteAsset

# 1x1 PNG (red) base64
PNG_1x1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
)

@pytest.fixture()
def client(request):
    fd, path = tempfile.mkstemp(prefix='panel_test_', suffix='.db')
    os.close(fd)
    try:
        from app import create_app
        local_app = create_app()
        local_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{path}'
        local_app.config['TESTING'] = True
        # enable DB storage for this test
        local_app.config['THEME_STORE_IN_DB'] = True
        local_app.config['THEME_UPLOAD_MAX_BYTES'] = 200000
        # expose `app` in the test module for compatibility
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


def make_admin(client):
    with app.app_context():
        a = User(first_name='Admin', last_name='User', email='admin+'+os.urandom(4).hex()+"@example.com", dob=date(1970,1,1), role='system_admin')
        a.set_password('x')
        db.session.add(a)
        db.session.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = a.id
        return a


def test_upload_and_serve_db_asset(client):
    make_admin(client)
    # fetch csrf token then upload file
    client.get('/admin/theme')
    token = session_csrf(client)
    # upload file
    data = {
        'csrf_token': token,
        'logo': (io.BytesIO(PNG_1x1), 'logo.png')
    }
    rv = client.post('/admin/theme?upload=1', data=data, follow_redirects=True)
    assert rv.status_code == 200

    # ensure asset exists in DB
    with app.app_context():
        sa = SiteAsset.query.filter_by(filename='logo.png').first()
        assert sa is not None
        assert sa.data.startswith(b'\x89PNG')
        aid = sa.id

    # fetch via id-based endpoint
    r = client.get(f'/theme_asset/id/{aid}')
    assert r.status_code == 200
    # Image is normalized to PNG but should still start with PNG magic bytes
    assert r.data.startswith(b'\x89PNG')
    assert r.headers.get('Content-Type','').startswith('image/')

    # fetch thumbnail
    rthumb = client.get(f'/theme_asset/thumb/{aid}')
    assert rthumb.status_code == 200
    assert rthumb.headers.get('Content-Type','').startswith('image/')

    # delete it by id
    rv2 = client.post('/admin/theme', data={'delete_asset_id': str(aid),'csrf_token':session_csrf(client)}, follow_redirects=True)
    assert rv2.status_code == 200
    assert b'Deleted' in rv2.data

    r2 = client.get(f'/theme_asset/id/{aid}')
    assert r2.status_code == 404


def session_csrf(client):
    # ensure csrf token exists via GET then read session
    client.get('/admin/theme')
    with client.session_transaction() as sess:
        return sess.get('csrf_token','')
