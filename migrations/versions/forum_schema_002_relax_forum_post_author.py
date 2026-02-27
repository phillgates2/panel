"""Relax forum_post.author nullability

Revision ID: forum_schema_002
Revises: forum_schema_001
Create Date: 2026-02-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "forum_schema_002"
down_revision = "forum_schema_001"
branch_labels = None
depends_on = None


def _get_table_names(inspector: sa.Inspector) -> set[str]:
    try:
        return set(inspector.get_table_names())
    except Exception:
        return set()


def _get_columns(inspector: sa.Inspector, table_name: str) -> dict[str, dict]:
    try:
        return {c["name"]: c for c in inspector.get_columns(table_name)}
    except Exception:
        return {}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "forum_post" not in _get_table_names(inspector):
        return

    cols = _get_columns(inspector, "forum_post")
    author_col = cols.get("author")
    if not author_col:
        return

    # Legacy schema had author NOT NULL (string). New code uses author_id.
    if author_col.get("nullable", True) is False:
        with op.batch_alter_table("forum_post", schema=None) as batch_op:
            batch_op.alter_column(
                "author",
                existing_type=sa.String(length=120),
                nullable=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "forum_post" not in _get_table_names(inspector):
        return

    cols = _get_columns(inspector, "forum_post")
    author_col = cols.get("author")
    if not author_col:
        return

    # Best-effort only: reverting to NOT NULL may fail if rows exist with NULL.
    if author_col.get("nullable", True) is True:
        try:
            with op.batch_alter_table("forum_post", schema=None) as batch_op:
                batch_op.alter_column(
                    "author",
                    existing_type=sa.String(length=120),
                    nullable=False,
                )
        except Exception:
            pass
