"""Create CMS and Forum tables

Revision ID: 20251118_add_cms_forum_tables
Revises: 
Create Date: 2025-11-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251118_add_cms_forum_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cms_page',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.String(length=255), nullable=False, unique=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'forum_thread',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'forum_post',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('thread_id', sa.Integer(), sa.ForeignKey('forum_thread.id'), nullable=False),
        sa.Column('author', sa.String(length=120), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('forum_post')
    op.drop_table('forum_thread')
    op.drop_table('cms_page')
