"""Update forum tables to match current models

Revision ID: forum_schema_001
Revises: cms_blog_post_001
Create Date: 2026-02-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "forum_schema_001"
down_revision = "cms_blog_post_001"
branch_labels = None
depends_on = None


def _get_table_names(inspector: sa.Inspector) -> set[str]:
    try:
        return set(inspector.get_table_names())
    except Exception:
        return set()


def _get_column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    try:
        return {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return set()


def _get_index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    try:
        return {i.get("name") for i in inspector.get_indexes(table_name) if i.get("name")}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    table_names = _get_table_names(inspector)

    # forum_thread
    if "forum_thread" in table_names:
        existing_cols = _get_column_names(inspector, "forum_thread")

        with op.batch_alter_table("forum_thread", schema=None) as batch_op:
            if "author_id" not in existing_cols:
                batch_op.add_column(sa.Column("author_id", sa.Integer(), nullable=True))
                try:
                    batch_op.create_foreign_key(
                        "fk_forum_thread_author_id_user",
                        "user",
                        ["author_id"],
                        ["id"],
                    )
                except Exception:
                    pass

            if "is_pinned" not in existing_cols:
                batch_op.add_column(
                    sa.Column(
                        "is_pinned",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("false"),
                    )
                )

            if "is_locked" not in existing_cols:
                batch_op.add_column(
                    sa.Column(
                        "is_locked",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("false"),
                    )
                )

        inspector = sa.inspect(op.get_bind())
        existing_indexes = _get_index_names(inspector, "forum_thread")
        if "idx_thread_author" not in existing_indexes and "author_id" in _get_column_names(
            inspector, "forum_thread"
        ):
            try:
                op.create_index("idx_thread_author", "forum_thread", ["author_id"])
            except Exception:
                pass

        # (is_pinned, created_at) composite index
        existing_indexes = _get_index_names(inspector, "forum_thread")
        cols = _get_column_names(inspector, "forum_thread")
        if (
            "idx_thread_pinned_created" not in existing_indexes
            and "is_pinned" in cols
            and "created_at" in cols
        ):
            try:
                op.create_index(
                    "idx_thread_pinned_created", "forum_thread", ["is_pinned", "created_at"]
                )
            except Exception:
                pass

    # forum_post
    if "forum_post" in table_names:
        existing_cols = _get_column_names(inspector, "forum_post")

        with op.batch_alter_table("forum_post", schema=None) as batch_op:
            if "author_id" not in existing_cols:
                batch_op.add_column(sa.Column("author_id", sa.Integer(), nullable=True))
                try:
                    batch_op.create_foreign_key(
                        "fk_forum_post_author_id_user",
                        "user",
                        ["author_id"],
                        ["id"],
                    )
                except Exception:
                    pass

        inspector = sa.inspect(op.get_bind())
        existing_indexes = _get_index_names(inspector, "forum_post")
        cols = _get_column_names(inspector, "forum_post")

        if "idx_post_thread" not in existing_indexes and "thread_id" in cols:
            try:
                op.create_index("idx_post_thread", "forum_post", ["thread_id"])
            except Exception:
                pass

        if "idx_post_author" not in existing_indexes and "author_id" in cols:
            try:
                op.create_index("idx_post_author", "forum_post", ["author_id"])
            except Exception:
                pass

        if "idx_post_created" not in existing_indexes and "created_at" in cols:
            try:
                op.create_index("idx_post_created", "forum_post", ["created_at"])
            except Exception:
                pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    table_names = _get_table_names(inspector)

    if "forum_post" in table_names:
        existing_indexes = _get_index_names(inspector, "forum_post")
        for idx in ("idx_post_created", "idx_post_author", "idx_post_thread"):
            if idx in existing_indexes:
                try:
                    op.drop_index(idx, table_name="forum_post")
                except Exception:
                    pass

        existing_cols = _get_column_names(inspector, "forum_post")
        with op.batch_alter_table("forum_post", schema=None) as batch_op:
            if "author_id" in existing_cols:
                try:
                    batch_op.drop_constraint("fk_forum_post_author_id_user", type_="foreignkey")
                except Exception:
                    pass
                try:
                    batch_op.drop_column("author_id")
                except Exception:
                    pass

    if "forum_thread" in table_names:
        existing_indexes = _get_index_names(inspector, "forum_thread")
        for idx in ("idx_thread_pinned_created", "idx_thread_author"):
            if idx in existing_indexes:
                try:
                    op.drop_index(idx, table_name="forum_thread")
                except Exception:
                    pass

        existing_cols = _get_column_names(inspector, "forum_thread")
        with op.batch_alter_table("forum_thread", schema=None) as batch_op:
            if "is_locked" in existing_cols:
                try:
                    batch_op.drop_column("is_locked")
                except Exception:
                    pass
            if "is_pinned" in existing_cols:
                try:
                    batch_op.drop_column("is_pinned")
                except Exception:
                    pass
            if "author_id" in existing_cols:
                try:
                    batch_op.drop_constraint("fk_forum_thread_author_id_user", type_="foreignkey")
                except Exception:
                    pass
                try:
                    batch_op.drop_column("author_id")
                except Exception:
                    pass
