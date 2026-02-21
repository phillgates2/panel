"""Add profile fields to User model

Revision ID: user_profile_001
Revises: user_api_tokens_001
Create Date: 2026-02-21

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "user_profile_001"
down_revision = "user_api_tokens_001"
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
        if "bio" not in existing_cols:
            batch_op.add_column(sa.Column("bio", sa.Text(), nullable=True))
        if "avatar" not in existing_cols:
            batch_op.add_column(sa.Column("avatar", sa.String(length=255), nullable=True))


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
        existing_cols = {c["name"] for c in inspector.get_columns("user")}
    except Exception:
        existing_cols = set()

    with op.batch_alter_table("user", schema=None) as batch_op:
        if "avatar" in existing_cols:
            batch_op.drop_column("avatar")
        if "bio" in existing_cols:
            batch_op.drop_column("bio")
