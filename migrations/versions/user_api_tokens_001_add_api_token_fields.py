"""Add API token fields to User model

Revision ID: user_api_tokens_001
Revises: merge_heads_20260221
Create Date: 2026-02-21

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "user_api_tokens_001"
down_revision = "merge_heads_20260221"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        table_names = set(inspector.get_table_names())
    except Exception:
        table_names = set()

    if "user" not in table_names:
        return

    try:
        existing_cols = {c["name"] for c in inspector.get_columns("user")}
    except Exception:
        existing_cols = set()

    with op.batch_alter_table("user", schema=None) as batch_op:
        if "api_token" not in existing_cols:
            batch_op.add_column(sa.Column("api_token", sa.String(length=128), nullable=True))
        if "api_token_created" not in existing_cols:
            batch_op.add_column(sa.Column("api_token_created", sa.DateTime(), nullable=True))
        if "api_token_last_used" not in existing_cols:
            batch_op.add_column(sa.Column("api_token_last_used", sa.DateTime(), nullable=True))

    # Create unique index for api_token (best-effort).
    inspector = sa.inspect(op.get_bind())
    try:
        indexes = inspector.get_indexes("user")
    except Exception:
        indexes = []

    index_names = {i.get("name") for i in indexes if i.get("name")}
    if "uq_user_api_token" not in index_names:
        try:
            op.create_index("uq_user_api_token", "user", ["api_token"], unique=True)
        except Exception:
            # If the index already exists under a different name or the column is missing,
            # we don't want to break upgrades.
            pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        table_names = set(inspector.get_table_names())
    except Exception:
        table_names = set()

    if "user" not in table_names:
        return

    try:
        indexes = inspector.get_indexes("user")
    except Exception:
        indexes = []

    index_names = {i.get("name") for i in indexes if i.get("name")}
    if "uq_user_api_token" in index_names:
        try:
            op.drop_index("uq_user_api_token", table_name="user")
        except Exception:
            pass

    try:
        existing_cols = {c["name"] for c in inspector.get_columns("user")}
    except Exception:
        existing_cols = set()

    with op.batch_alter_table("user", schema=None) as batch_op:
        if "api_token_last_used" in existing_cols:
            batch_op.drop_column("api_token_last_used")
        if "api_token_created" in existing_cols:
            batch_op.drop_column("api_token_created")
        if "api_token" in existing_cols:
            batch_op.drop_column("api_token")
