#!/usr/bin/env python3
"""Verify live database connectivity + schema state.

Designed to be copy/paste-safe in production (avoids heredoc quoting issues).

Reads DB configuration from (in order):
- DATABASE_URL
- SQLALCHEMY_DATABASE_URI
- PANEL_DB_* split vars

Exits non-zero if the DB is unreachable, the `user` table is missing, or the
Alembic version table is missing/unreadable.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def _build_db_url_from_env() -> str:
    override = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("SQLALCHEMY_DATABASE_URI")
        or os.environ.get("PANEL_DATABASE_URL")
    )
    if isinstance(override, str) and override.strip():
        url = override.strip()
    else:
        user = os.environ.get("PANEL_DB_USER", "paneluser")
        password = (
            os.environ.get("PANEL_DB_PASS")
            or os.environ.get("PANEL_DB_PASSWORD")
            or "panelpass"
        )
        host = os.environ.get("PANEL_DB_HOST", "127.0.0.1")
        port = os.environ.get("PANEL_DB_PORT", "5432")
        name = os.environ.get("PANEL_DB_NAME", "paneldb")
        url = (
            f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{name}"
        )

    if url.lower().startswith("sqlite"):
        raise ValueError(
            "SQLite is not supported. Configure PostgreSQL via DATABASE_URL/SQLALCHEMY_DATABASE_URI or PANEL_DB_*."
        )
    if not url.lower().startswith("postgres"):
        raise ValueError(f"Unsupported database URL scheme: {url.split(':', 1)[0]}")
    return url


def _mask_db_url(url: str) -> str:
    # Avoid leaking credentials; keep scheme/host/db visible.
    if "://" not in url or "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    creds_and_host = rest.split("@", 1)
    if len(creds_and_host) != 2:
        return url
    return f"{scheme}://***@{creds_and_host[1]}"


def main() -> int:
    try:
        url = _build_db_url_from_env()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"DB URL: {_mask_db_url(url)}")

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            current_db = conn.execute(text("select current_database()")).scalar_one()
            current_schema = conn.execute(text("select current_schema()")).scalar_one()
            search_path = conn.execute(text("show search_path")).scalar_one()

            print(f"current_database(): {current_db}")
            print(f"current_schema(): {current_schema}")
            print(f"search_path: {search_path}")

            user_table_schemas = conn.execute(
                text(
                    """
                    select table_schema
                    from information_schema.tables
                    where table_name = 'user'
                    order by table_schema
                    """
                )
            ).scalars().all()

            if user_table_schemas:
                print(f"✓ Found table 'user' in schema(s): {', '.join(user_table_schemas)}")
            else:
                print("✗ Missing table 'user' (no rows in information_schema.tables)")
                return 3

            # Alembic version table check
            has_alembic = conn.execute(
                text(
                    """
                    select 1
                    from information_schema.tables
                    where table_name = 'alembic_version'
                    limit 1
                    """
                )
            ).scalar() is not None

            if not has_alembic:
                print("✗ Missing 'alembic_version' table")
                return 4

            version = conn.execute(
                text("select version_num from alembic_version")
            ).scalar_one_or_none()
            print(f"alembic_version: {version}")

    except SQLAlchemyError as exc:
        print(f"ERROR: DB query failed: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
