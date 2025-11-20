"""Add Ptero-Eggs tracking tables

Revision ID: ptero_eggs_001
Revises: 
Create Date: 2025-11-20 00:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ptero_eggs_001'
down_revision = None  # Set this to your latest migration revision
branch_labels = None
depends_on = None


def upgrade():
    # Create ptero_eggs_update_metadata table
    op.create_table(
        'ptero_eggs_update_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_url', sa.String(length=255), nullable=False, server_default='https://github.com/Ptero-Eggs/game-eggs.git'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_commit_hash', sa.String(length=64), nullable=True),
        sa.Column('last_commit_message', sa.Text(), nullable=True),
        sa.Column('last_sync_status', sa.String(length=32), nullable=False, server_default='never'),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('total_templates_imported', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('templates_updated', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('templates_added', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ptero_eggs_template_version table
    op.create_table(
        'ptero_eggs_template_version',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('commit_hash', sa.String(length=64), nullable=True),
        sa.Column('template_data_snapshot', sa.Text(), nullable=False),
        sa.Column('changes_summary', sa.Text(), nullable=True),
        sa.Column('imported_at', sa.DateTime(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=True, server_default='1'),
        sa.ForeignKeyConstraint(['template_id'], ['config_template.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create index for faster queries
    op.create_index('ix_ptero_template_version_template_id', 'ptero_eggs_template_version', ['template_id'])
    op.create_index('ix_ptero_template_version_current', 'ptero_eggs_template_version', ['is_current'])


def downgrade():
    op.drop_index('ix_ptero_template_version_current', table_name='ptero_eggs_template_version')
    op.drop_index('ix_ptero_template_version_template_id', table_name='ptero_eggs_template_version')
    op.drop_table('ptero_eggs_template_version')
    op.drop_table('ptero_eggs_update_metadata')
