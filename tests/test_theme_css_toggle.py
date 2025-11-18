import os
import pathlib
import sys

os.environ["PANEL_USE_SQLITE"] = "1"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import os
import tempfile

import pytest

from app import SiteSetting, app, db


@pytest.fixture()
def client(request):
    fd, path = tempfile.mkstemp(prefix="panel_test_", suffix=".db")
    os.close(fd)
    try:
        from app import create_app

        local_app = create_app()
        local_app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{path}"
        local_app.config["TESTING"] = True
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
