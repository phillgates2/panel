#!/usr/bin/env python3
"""Probe all Flask GET routes for basic health.

This checks *routes*, not just linked pages, by iterating `app.url_map`.
It supports an optional login step (cookie-based) so you can validate
both logged-out and logged-in behavior.

Usage:
  python tools/route_probe.py http://127.0.0.1:5000/
  python tools/route_probe.py http://127.0.0.1:5000/ --login-email admin@panel.local --login-password admin123

Exit codes:
  0: No 4xx/5xx (excluding allowed auth-gated statuses when logged out)
  2: Failures found
"""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from datetime import date

# Ensure repo root is on sys.path when running from tools/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@dataclasses.dataclass(frozen=True)
class Result:
    status: int
    url: str


def _build_opener() -> urllib.request.OpenerDirector:
    jar = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _ensure_login_user(email: str, password: str) -> None:
    """Ensure the login user exists for dev probing.

    The probe is intended for local/dev environments where the database may be
    empty. Creating the user here avoids requiring separate seeding steps.
    """

    try:
        from werkzeug.security import generate_password_hash

        from app import app as flask_app  # type: ignore
        from app import db  # type: ignore
        from src.panel.models import User  # type: ignore
    except Exception:
        return

    try:
        with flask_app.app_context():
            existing = db.session.query(User).filter_by(email=email).first()
            if existing:
                try:
                    if existing.check_password(password):
                        return
                except Exception:
                    pass
                existing.password_hash = generate_password_hash(password)
                db.session.commit()
                return
            user = User(
                first_name="Admin",
                last_name="User",
                email=email,
                dob=date(1990, 1, 1),
                role="system_admin",
            )
            # Bypass password complexity rules for probe user creation.
            user.password_hash = generate_password_hash(password)
            db.session.add(user)
            db.session.commit()
    except Exception:
        # Best-effort only; probing can still proceed logged-out.
        return


def _fetch(
    opener: urllib.request.OpenerDirector,
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    timeout: float = 3.0,
) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"User-Agent": "panel-route-probe"},
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            return status, resp.geturl()
    except urllib.error.HTTPError as e:
        return int(getattr(e, "code", 0) or 0), url
    except Exception:
        return 0, url


def _join(base: str, path: str) -> str:
    return urllib.parse.urljoin(base, path)


def _make_value(converter: str) -> str:
    c = (converter or "").lower()
    if c in {"int", "integer"}:
        return "1"
    if c in {"float"}:
        return "1.0"
    if c in {"uuid"}:
        return "00000000-0000-0000-0000-000000000000"
    if c in {"path"}:
        return "test"
    return "test"


def _materialize(rule: str) -> str:
    # Replace <converter:name> or <name> with dummy values.
    def repl(m: re.Match[str]) -> str:
        converter = m.group("conv") or "string"
        return _make_value(converter)

    return re.sub(r"<(?:(?P<conv>[^:>]+):)?(?P<name>[^>]+)>", repl, rule)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base_url")
    ap.add_argument("--login-email")
    ap.add_argument("--login-password")
    ap.add_argument("--login-path", default="/login")
    ap.add_argument("--timeout", type=float, default=3.0)
    ap.add_argument("--max-routes", type=int, default=0)
    ap.add_argument("--print-every", type=int, default=50)
    args = ap.parse_args()

    base = args.base_url
    if not base.endswith("/"):
        base += "/"

    opener = _build_opener()

    # Optional login
    if args.login_email and args.login_password:
        _ensure_login_user(args.login_email, args.login_password)
        login_url = _join(base, args.login_path.lstrip("/"))
        form = urllib.parse.urlencode({"email": args.login_email, "password": args.login_password}).encode("utf-8")
        _fetch(opener, login_url, method="POST", data=form, timeout=args.timeout)
        # Verify session by hitting /metrics (requires session user_id)
        st, _ = _fetch(opener, _join(base, "metrics"), timeout=args.timeout)
        if st != 200:
            print(f"Login verification failed: GET /metrics => {st}")
            return 2

    # Import Flask app to enumerate routes
    try:
        from app import app as flask_app  # type: ignore
    except Exception as e:
        print(f"Failed to import Flask app: {e}")
        return 2

    failures: list[Result] = []
    auth_gated: list[Result] = []

    routes = [r for r in flask_app.url_map.iter_rules()]
    total = 0
    for rule in routes:
        methods = getattr(rule, "methods", set()) or set()
        if "GET" not in methods:
            continue
        path = getattr(rule, "rule", "")
        if not path or path.startswith("/static/"):
            continue
        if path.rstrip("/") in {"/logout"}:
            continue

        url = _join(base, _materialize(path).lstrip("/"))
        total += 1
        if args.print_every and total % args.print_every == 0:
            print(f"... probed {total} routes", file=sys.stderr)

        status, _ = _fetch(opener, url, timeout=args.timeout)

        # Logged-out: treat auth-gated as expected
        if not (args.login_email and args.login_password) and status in {401, 403}:
            auth_gated.append(Result(status=status, url=url))
            continue

        if status == 0 or status >= 400:
            failures.append(Result(status=status, url=url))

        if args.max_routes and total >= args.max_routes:
            break

    if failures:
        print("FAILURES:")
        for r in sorted(failures, key=lambda x: (x.status, x.url)):
            print(f"  {r.status:>3}  {r.url}")
        if auth_gated:
            print("\nAUTH-GATED (expected while logged out):")
            for r in sorted(auth_gated, key=lambda x: (x.status, x.url))[:50]:
                print(f"  {r.status:>3}  {r.url}")
            if len(auth_gated) > 50:
                print(f"  ... ({len(auth_gated) - 50} more)")
        return 2

    if auth_gated and not (args.login_email and args.login_password):
        print(f"OK: no 4xx/5xx; auth-gated endpoints: {len(auth_gated)}")
    else:
        print("OK: no 4xx/5xx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
