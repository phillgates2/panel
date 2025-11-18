import os
os.environ['PANEL_USE_SQLITE'] = '1'
import pytest
from datetime import date
from app import app, db, User

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


def test_register_and_login(client):
    with app.app_context():
        u = User(first_name='Test', last_name='User', email='t@example.com', dob=date(2000,1,1))
        u.set_password('Password1!')
        db.session.add(u)
        db.session.commit()
        fetched = User.query.filter_by(email='t@example.com').first()
        assert fetched is not None
        assert fetched.check_password('Password1!')
