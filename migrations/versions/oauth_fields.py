"""
Add OAuth fields to User model
Revision ID: oauth_fields
Revises: None
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'oauth_fields'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Add OAuth fields to user table."""
    op.add_column('user', sa.Column('oauth_provider', sa.String(length=32), nullable=True))
    op.add_column('user', sa.Column('oauth_id', sa.String(length=128), nullable=True))
    op.add_column('user', sa.Column('oauth_token', sa.Text(), nullable=True))
    op.add_column('user', sa.Column('oauth_refresh_token', sa.Text(), nullable=True))
    op.add_column('user', sa.Column('oauth_token_expires', sa.DateTime(), nullable=True))

    # Create unique index on oauth_id
    op.create_unique_constraint('uq_user_oauth_id', 'user', ['oauth_id'])

def downgrade():
    """Remove OAuth fields from user table."""
    op.drop_constraint('uq_user_oauth_id', 'user', type_='unique')
    op.drop_column('user', 'oauth_token_expires')
    op.drop_column('user', 'oauth_refresh_token')
    op.drop_column('user', 'oauth_token')
    op.drop_column('user', 'oauth_id')
    op.drop_column('user', 'oauth_provider')