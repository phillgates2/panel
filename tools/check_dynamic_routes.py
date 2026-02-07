"""Quick diagnostic script to exercise key dynamic routes.

Usage (from repo root):

    PANEL_USE_SQLITE=1 python -m tools.check_dynamic_routes

This boots the app in testing mode, seeds a minimal set of
objects (dedicated test user, server, forum thread), and then issues
GET and POST requests to a handful of important parameterised routes
to ensure they return non-error responses.
"""

from __future__ import annotations

import json as _json
import sys
from typing import Dict, Iterable, List, Optional, Tuple

from app import create_app, db
from models import User
from src.panel.models import Server
from src.panel.forum import Post, Thread


TEST_USER_EMAIL = "route-write-tester@example.com"
TEST_USER_PASSWORD = "Password123!"
TEST_CSRF_TOKEN = "test-csrf-token"


def seed_data() -> Tuple[User, Server, Server, Thread]:
    """Create a minimal set of objects for dynamic routes.

    Returns (user, server, thread).
    """

    # Dedicated test user (used for authenticated GETs and write endpoints)
    user = User(
        first_name="Route",
        last_name="WriteTester",
        email=TEST_USER_EMAIL,
        dob="1990-01-01",
        role="system_admin",
    )
    user.set_password(TEST_USER_PASSWORD)
    db.session.add(user)
    db.session.flush()  # ensure user.id is available

    # Minimal server used for safe server-write endpoints (e.g. config versions)
    server = Server(
        name="Test Server",
        host="127.0.0.1",
        port=27960,
        rcon_password="changeme",
        owner_id=user.id,
    )
    db.session.add(server)

    # Separate server used for delete endpoint checks to avoid FK constraints
    # (e.g. if config versions were created for the primary server).
    deletable_server = Server(
        name="Delete Me Server",
        host="127.0.0.1",
        port=27961,
        rcon_password="changeme",
        owner_id=user.id,
    )
    db.session.add(deletable_server)

    # Minimal forum thread and first post
    thread = Thread(title="Test Thread", author_id=user.id)
    db.session.add(thread)
    db.session.flush()  # ensure thread.id is available

    post = Post(thread_id=thread.id, author_id=user.id, content="Seed content")
    db.session.add(post)

    db.session.commit()
    return user, server, deletable_server, thread


def login_as_test_user(client, user_id: int) -> int:
    """Authenticate the dedicated test user.

    Uses the normal /login flow when possible, but falls back to
    session-based authentication to keep this diagnostic script
    resilient to template/auth changes.
    """

    resp = client.post(
        "/login",
        data={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        follow_redirects=False,
    )

    # If the POST didn't establish a session, force it.
    try:
        with client.session_transaction() as sess:
            if not sess.get("user_id") and not sess.get("_user_id"):
                sess["user_id"] = user_id
                # Flask-Login compatibility
                sess["_user_id"] = str(user_id)
                sess["_fresh"] = True
    except Exception:
        pass

    return resp.status_code


def ensure_csrf_token(client, token: str = TEST_CSRF_TOKEN) -> str:
    with client.session_transaction() as sess:
        sess["csrf_token"] = token
    return token


def _is_server_error(status_code: int) -> bool:
    return status_code >= 500


def _rule_exists(app, path: str, method: str = "GET") -> bool:
    try:
        for rule in app.url_map.iter_rules():
            if rule.rule == path and method.upper() in (rule.methods or set()):
                return True
    except Exception:
        return False
    return False


def _should_skip_route(app, path: str, method: str) -> bool:
    """Skip checks for routes that are not registered.

    This avoids treating optional blueprints (e.g. server management) as failures.
    """

    # If the route is static, we can check directly.
    if "<" not in path:
        return not _rule_exists(app, path, method)
    # For dynamic rules, best-effort: if a concrete sample path 404s but the
    # app has no matching rules, it's likely an unregistered blueprint.
    return False


def main() -> int:
    app = create_app("testing")
    with app.app_context():
        db.create_all()

        user, server, deletable_server, thread = seed_data()

        client = app.test_client()

        # Stub out RCON execution so exercising server routes never performs
        # real network calls during this diagnostic run.
        try:
            import src.panel.server_management as _server_mgmt

            def _stub_execute_rcon_command(server_obj, command: str) -> str:
                return f"stubbed:{command}"

            _server_mgmt.execute_rcon_command = _stub_execute_rcon_command  # type: ignore[attr-defined]
        except Exception:
            # Best-effort: if server management isn't available, continue.
            pass

        print("Logging in as dedicated test user...")
        login_code = login_as_test_user(client, user.id)
        print(f"/login: {login_code}")
        if login_code not in (200, 302):
            print("Login failed; cannot exercise authenticated write endpoints.")
            return 1

        # --- GET checks (avoid endpoints that may hit real external services) ---
        get_routes: List[str] = [
            "/",  # sanity
            "/status",
            # Server management routes are optional depending on blueprint registration.
            f"/servers/{server.id}",
            f"/servers/{server.id}/rcon",  # GET should not execute commands
            f"/admin/servers/{server.id}/manage-users",
            f"/forum/thread/{thread.id}",
        ]

        print("\nChecking dynamic GET routes...")
        failed: List[Tuple[str, int]] = []
        for path in get_routes:
            # Skip obvious optional server-management routes if that blueprint isn't registered.
            if path.startswith("/servers/") and not any(
                r.rule.startswith("/servers") for r in app.url_map.iter_rules()
            ):
                print(f"GET {path}: SKIP (server management blueprint not registered)")
                continue

            resp = client.get(path)
            print(f"GET {path}: {resp.status_code}")
            if _is_server_error(resp.status_code):
                failed.append((f"GET {path}", resp.status_code))

        # --- POST checks (write endpoints) ---
        print("\nChecking dynamic POST write endpoints...")
        csrf_token = ensure_csrf_token(client)

        # 1) Create a new thread (CSRF relaxed for tests in implementation)
        create_thread_resp = client.post(
            "/forum/thread/create",
            data={"title": "Write Check Thread", "content": "Write check seed content"},
            follow_redirects=False,
        )
        print(f"POST /forum/thread/create: {create_thread_resp.status_code}")
        if _is_server_error(create_thread_resp.status_code):
            failed.append(("POST /forum/thread/create", create_thread_resp.status_code))

        created_thread = (
            db.session.query(Thread)
            .filter(Thread.title == "Write Check Thread")
            .order_by(Thread.id.desc())
            .first()
        )
        if not created_thread:
            failed.append(("POST /forum/thread/create (no thread created)", 0))
        else:
            # 2) Reply to the seeded thread (requires CSRF + login)
            before_count = db.session.query(Post).filter_by(thread_id=thread.id).count()
            reply_resp = client.post(
                f"/forum/thread/{thread.id}/reply",
                data={"content": "Automated reply", "csrf_token": csrf_token},
                follow_redirects=False,
            )
            print(f"POST /forum/thread/{thread.id}/reply: {reply_resp.status_code}")
            if _is_server_error(reply_resp.status_code):
                failed.append((f"POST /forum/thread/{thread.id}/reply", reply_resp.status_code))
            after_count = db.session.query(Post).filter_by(thread_id=thread.id).count()
            if after_count != before_count + 1:
                failed.append(("POST forum reply (post count did not increase)", 0))

        # 3) Server action write endpoint: create a config version (JSON API)
        config_payload: Dict[str, object] = {
            "config_data": {
                "server_cfg": "\n".join(
                    [
                        'set sv_hostname "Route Check"',
                        'set rconpassword "changeme"',
                        "set sv_maxclients 8",
                    ]
                )
            },
            "change_summary": "route-check",
        }
        config_create_resp = client.post(
            f"/server/{server.id}/config/create",
            json=config_payload,
        )
        print(
            f"POST /server/{server.id}/config/create: {config_create_resp.status_code}"
        )
        if _is_server_error(config_create_resp.status_code):
            failed.append(
                (
                    f"POST /server/{server.id}/config/create",
                    config_create_resp.status_code,
                )
            )

        # 4) Server action write endpoint: RCON execute (stubbed)
        rcon_execute_resp = client.post(
            f"/servers/{server.id}/rcon/execute",
            data=_json.dumps({"command": "status"}),
            content_type="application/json",
        )
        print(
            f"POST /servers/{server.id}/rcon/execute: {rcon_execute_resp.status_code}"
        )
        if _is_server_error(rcon_execute_resp.status_code):
            try:
                body_preview = (rcon_execute_resp.get_data(as_text=True) or "")[:500]
                if body_preview:
                    print(f"  body: {body_preview}")
            except Exception:
                pass
            failed.append(
                (
                    f"POST /servers/{server.id}/rcon/execute",
                    rcon_execute_resp.status_code,
                )
            )
        else:
            try:
                payload = rcon_execute_resp.get_json(silent=True) or {}
                result = payload.get("result")
                if isinstance(result, str) and not result.startswith("stubbed:"):
                    failed.append(("POST rcon execute (unexpected non-stub result)", 0))
            except Exception:
                # If response isn't JSON, don't fail the run; status code check above
                # already guards against server errors.
                pass

        # 5) Server-related write endpoint: admin delete (no CSRF required)
        delete_resp = client.post(
            f"/admin/servers/{deletable_server.id}/delete",
            data={},
            follow_redirects=False,
        )
        print(
            f"POST /admin/servers/{deletable_server.id}/delete: {delete_resp.status_code}"
        )
        if _is_server_error(delete_resp.status_code):
            failed.append((f"POST /admin/servers/{server.id}/delete", delete_resp.status_code))

        # Verify deletion using a fresh session to avoid identity-map artifacts.
        try:
            db.session.remove()
        except Exception:
            try:
                db.session.expire_all()
            except Exception:
                pass

        deleted_still_exists = (
            db.session.query(Server.id)
            .filter(Server.id == deletable_server.id)
            .first()
            is not None
        )
        if deleted_still_exists:
            failed.append(("POST admin delete server (server still exists)", 0))

        if failed:
            print("\nSome dynamic route checks failed:")
            for path, code in failed:
                if code:
                    print(f"  {code} -> {path}")
                else:
                    print(f"  FAIL -> {path}")
            return 1

        print("\nAll checked dynamic GET/POST routes completed without server errors.")
        return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
