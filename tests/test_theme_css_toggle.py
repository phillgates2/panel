import os
import pathlib
import sys
from urllib.parse import urlparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import os
import tempfile

import pytest

from app import SiteSetting, app, db


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


def test_theme_link_and_css_serving(client):
    with app.app_context():
        # set CSS and enabled flag in DB
        css = "body{background:#123456;}"
        s_css = SiteSetting.query.filter_by(key="custom_theme_css").first()
        if not s_css:
            s_css = SiteSetting(key="custom_theme_css", value=css)
            db.session.add(s_css)
        else:
            s_css.value = css
        s_flag = SiteSetting.query.filter_by(key="theme_enabled").first()
        if not s_flag:
            s_flag = SiteSetting(key="theme_enabled", value="1")
            db.session.add(s_flag)
        else:
            s_flag.value = "1"
        db.session.commit()

        # request home page - should include link to /theme.css
        r = client.get("/")
        assert r.status_code == 200
        html = r.data.decode("utf-8")
        assert "/theme.css" in html

        # request theme.css
        r2 = client.get("/theme.css")
        assert r2.status_code == 200
        assert r2.data.decode("utf-8") == css
        assert r2.headers.get("Content-Type", "").startswith("text/css")

        # disable theme and verify link removed
        s_flag.value = "0"
        db.session.add(s_flag)
        db.session.commit()
        r3 = client.get("/")
        assert "/theme.css" not in r3.data.decode("utf-8")
