"""Add CMS blog post table

Revision ID: cms_blog_post_001
Revises: user_profile_001
Create Date: 2026-02-21

"""

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "cms_blog_post_001"
down_revision = "user_profile_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        table_names = set(inspector.get_table_names())
    except Exception:
        table_names = set()

    # If the core tables aren't present yet, earlier migrations should be run
    # first. This migration is a no-op in that scenario.
    if "user" not in table_names:
        return

    if "cms_blog_post" in table_names:
        return

    op.create_table(
        "cms_blog_post",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.String(length=500), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        table_names = set(inspector.get_table_names())
    except Exception:
        table_names = set()

    if "cms_blog_post" not in table_names:
        return

    op.drop_table("cms_blog_post")
