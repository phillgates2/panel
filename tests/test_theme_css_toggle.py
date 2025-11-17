import os
import sys
import pathlib
os.environ['PANEL_USE_SQLITE'] = '1'
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from datetime import date
from app import app, db, User, SiteSetting

@pytest.fixture()
def client():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_theme_link_and_css_serving(client):
    with app.app_context():
        # set CSS and enabled flag in DB
        css = 'body{background:#123456;}'
        s_css = SiteSetting(key='custom_theme_css', value=css)
        s_flag = SiteSetting(key='theme_enabled', value='1')
        db.session.add(s_css)
        db.session.add(s_flag)
        db.session.commit()

        # request home page - should include link to /theme.css
        r = client.get('/')
        assert r.status_code == 200
        html = r.data.decode('utf-8')
        assert '/theme.css' in html

        # request theme.css
        r2 = client.get('/theme.css')
        assert r2.status_code == 200
        assert r2.data.decode('utf-8') == css
        assert r2.headers.get('Content-Type', '').startswith('text/css')

        # disable theme and verify link removed
        s_flag.value = '0'
        db.session.add(s_flag)
        db.session.commit()
        r3 = client.get('/')
        assert '/theme.css' not in r3.data.decode('utf-8')
