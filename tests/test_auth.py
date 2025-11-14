import os
os.environ['PANEL_USE_SQLITE'] = '1'
import pytest
from datetime import date
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


def test_register_and_login(client):
    with app.app_context():
        u = User(first_name='Test', last_name='User', email='t@example.com', dob=date(2000,1,1))
        u.set_password('Password1!')
        db.session.add(u)
        db.session.commit()
        fetched = User.query.filter_by(email='t@example.com').first()
        assert fetched is not None
        assert fetched.check_password('Password1!')
