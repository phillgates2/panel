import base64
import io
import os
import pathlib
import sys
from datetime import date
from urllib.parse import urlparse

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import SiteAsset, User, app, db

# 1x1 PNG (red) base64
PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)


def _get_test_db_url() -> str:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        pytest.skip("Set DATABASE_URL to run tests (PostgreSQL-only)")

    if db_url.startswith("postgresql+psycopg2://"):
        db_url = "postgresql://" + db_url[len("postgresql+psycopg2://") :]

    if "test" not in (urlparse(db_url).path or "").lower():
        pytest.skip("DATABASE_URL must point to a test database")

    return db_url


@pytest.fixture()
def client(request):
    from app import create_app

    local_app = create_app()
    local_app.config["SQLALCHEMY_DATABASE_URI"] = _get_test_db_url()
    local_app.config["TESTING"] = True
    local_app.config["THEME_STORE_IN_DB"] = True
    local_app.config["THEME_UPLOAD_MAX_BYTES"] = 200000

    request.module.app = local_app

    with local_app.app_context():
        db.create_all()
        yield local_app.test_client()
        db.session.remove()
        db.drop_all()


def make_admin(client):
    with app.app_context():
        a = User(
            first_name="Admin",
            last_name="User",
            email="admin+" + os.urandom(4).hex() + "@example.com",
            dob=date(1970, 1, 1),
            role="system_admin",
        )
        a.set_password("x")
        db.session.add(a)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["user_id"] = a.id
        return a


def test_theme_asset_upload_and_serving(client):
    make_admin(client)

    # Upload a tiny PNG
    data = {
        "file": (io.BytesIO(PNG_1x1), "tiny.png"),
        "asset_type": "theme",
    }
    r = client.post("/admin/theme/assets/upload", data=data, content_type="multipart/form-data")
    assert r.status_code in (200, 302)

    with app.app_context():
        asset = SiteAsset.query.filter_by(filename="tiny.png").first()
        assert asset is not None

    # Asset should be retrievable (route may vary; keep it basic)
    r2 = client.get("/admin/theme/assets")
    assert r2.status_code == 200
