import os
from urllib.parse import urlparse

import asyncio
from datetime import date

import pytest

pytestmark = pytest.mark.e2e

from app import Server, User, app, db

try:
    from playwright.async_api import async_playwright  # type: ignore
except Exception:
    async_playwright = None


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def test_app():
    """Setup test app."""
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        pytest.skip("Set DATABASE_URL to run e2e tests (PostgreSQL-only)")
    if db_url.startswith("postgresql+psycopg2://"):
        db_url = "postgresql://" + db_url[len("postgresql+psycopg2://") :]
    if "test" not in (urlparse(db_url).path or "").lower():
        pytest.skip("DATABASE_URL must point to a test database")

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["TESTING"] = True
    try:
        with app.app_context():
            try:
                db.engine.dispose()
            except Exception:
                pass
            db.create_all()
            yield app
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()


def make_admin_and_server(app):
    """Create admin user and test server."""
    with app.app_context():
        admin = User(
            first_name="Test",
            last_name="Admin",
            email="admin@test.com",
            dob=date(1990, 1, 1),
        )
        admin.set_password("Password1!")
        admin.role = "system_admin"
        db.session.add(admin)
        db.session.commit()

        server = Server(
            name="test-server",
            description="Test",
            variables_json="{}",
            raw_config="# test",
        )
        db.session.add(server)
        db.session.commit()

        return admin.id, server.id


@pytest.mark.asyncio
async def test_modal_confirm_delete_server(test_app):
    """Test that delete button shows modal and confirms deletion."""
    if async_playwright is None:
        pytest.skip("playwright not available in this environment")
    admin_id, server_id = make_admin_and_server(test_app)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Start the Flask app in a thread
        from threading import Thread

        from werkzeug.serving import make_server

        server = make_server("localhost", 5555, test_app, threaded=True)
        server_thread = Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            # Login
            await page.goto("http://localhost:5555/login")
            await page.fill('input[name="email"]', "admin@test.com")
            await page.fill('input[name="password"]', "Password1!")
            await page.click('button[type="submit"]')
            # Wait for network to be idle rather than specific URL
            await page.wait_for_load_state('networkidle')

            # Navigate to admin servers
            await page.goto("http://localhost:5555/admin/servers")

            # Wait for page to load
            await page.wait_for_selector("table")

            # Click delete button
            delete_btn = await page.query_selector(".confirm-btn")
            assert delete_btn is not None, "Delete button not found"

            # Click the button which should trigger the modal
            await delete_btn.click()

            # Check modal is visible
            modal = await page.query_selector("#confirm-modal")
            modal_display = await modal.evaluate(
                "el => window.getComputedStyle(el).display"
            )
            assert modal_display == "block", "Modal should be visible"

            # Check message text
            message = await page.text_content("#confirm-message")
            assert (
                "test-server" in message
            ), f"Modal message should contain server name, got: {message}"

            # Click OK to confirm
            await page.click("#confirm-ok")

            # Wait for redirect and check server is deleted
            await page.wait_for_load_state('networkidle')

            # Verify server is gone from table
            with test_app.app_context():
                from app import Server

                deleted = db.session.query(Server).filter_by(id=server_id).first()
                assert deleted is None, "Server should be deleted"

        finally:
            await browser.close()
            server.shutdown()


@pytest.mark.asyncio
async def test_modal_cancel_delete(test_app):
    """Test that cancel button closes modal without deletion."""
    if async_playwright is None:
        pytest.skip("playwright not available in this environment")
    admin_id, server_id = make_admin_and_server(test_app)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        from threading import Thread

        from werkzeug.serving import make_server

        server = make_server("localhost", 5556, test_app, threaded=True)
        server_thread = Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            await page.goto("http://localhost:5556/login")
            await page.fill('input[name="email"]', "admin@test.com")
            await page.fill('input[name="password"]', "Password1!")
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')

            await page.goto("http://localhost:5556/admin/servers")
            await page.wait_for_selector("table")

            delete_btn = await page.query_selector(".confirm-btn")
            await delete_btn.click()

            # Check modal is visible
            modal = await page.query_selector("#confirm-modal")
            modal_display = await modal.evaluate(
                "el => window.getComputedStyle(el).display"
            )
            assert modal_display == "block"

            # Click Cancel
            await page.click("#confirm-cancel")

            # Modal should close
            await page.wait_for_function(
                "() => document.getElementById('confirm-modal').style.display === 'none'"
            )

            # Check server still exists
            with test_app.app_context():
                from app import Server

                still_exists = db.session.query(Server).filter_by(id=server_id).first()
                assert (
                    still_exists is not None
                ), "Server should still exist after cancel"

        finally:
            await browser.close()
            server.shutdown()


@pytest.mark.asyncio
async def test_modal_escape_key(test_app):
    """Test that ESC key closes modal."""
    if async_playwright is None:
        pytest.skip("playwright not available in this environment")
    admin_id, server_id = make_admin_and_server(test_app)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        from threading import Thread

        from werkzeug.serving import make_server

        server = make_server("localhost", 5557, test_app, threaded=True)
        server_thread = Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            await page.goto("http://localhost:5557/login")
            await page.fill('input[name="email"]', "admin@test.com")
            await page.fill('input[name="password"]', "Password1!")
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')

            await page.goto("http://localhost:5557/admin/servers")
            await page.wait_for_selector("table")

            delete_btn = await page.query_selector(".confirm-btn")
            await delete_btn.click()

            # Press ESC
            await page.press("body", "Escape")

            # Modal should close
            await page.wait_for_function(
                "() => document.getElementById('confirm-modal').style.display === 'none'"
            )

            # Check server still exists
            with test_app.app_context():
                from app import Server

                still_exists = db.session.query(Server).filter_by(id=server_id).first()
                assert still_exists is not None

        finally:
            await browser.close()
            server.shutdown()
