"""Add audit_log.ip_address and audit_log.user_agent

Revision ID: audit_log_001_add_ip_user_agent
Revises: forum_schema_002
Create Date: 2026-03-06

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "audit_log_001_add_ip_user_agent"
down_revision = "forum_schema_002"
branch_labels = None
depends_on = None


def _get_table_names(inspector: sa.Inspector) -> set[str]:
    try:
        return set(inspector.get_table_names())
    except Exception:
        return set()


def _get_columns(inspector: sa.Inspector, table_name: str) -> set[str]:
    try:
        return {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "audit_log" not in _get_table_names(inspector):
        return

    cols = _get_columns(inspector, "audit_log")

    if "ip_address" not in cols:
        op.add_column(
            "audit_log",
            sa.Column("ip_address", sa.String(length=45), nullable=True),
        )

    if "user_agent" not in cols:
        op.add_column(
            "audit_log",
            sa.Column("user_agent", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "audit_log" not in _get_table_names(inspector):
        return

    cols = _get_columns(inspector, "audit_log")

    if "user_agent" in cols:
        op.drop_column("audit_log", "user_agent")

    if "ip_address" in cols:
        op.drop_column("audit_log", "ip_address")
