"""Add config templates/versioning tables

Revision ID: config_templates_001
Revises: 2ca607eff9c8
Create Date: 2026-02-21

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "config_templates_001"
down_revision = "2ca607eff9c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "config_template",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("game_type", sa.String(length=32), nullable=False),
        sa.Column("template_data", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=True, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "config_version",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("config_data", sa.Text(), nullable=False),
        sa.Column("config_hash", sa.String(length=64), nullable=False),
        sa.Column("change_summary", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("deployed_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["server_id"], ["server.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "config_deployment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config_version_id", sa.Integer(), nullable=False),
        sa.Column("deployment_status", sa.String(length=32), nullable=False),
        sa.Column("deployment_log", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("deployed_by", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["config_version_id"], ["config_version.id"]),
        sa.ForeignKeyConstraint(["deployed_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("config_deployment")
    op.drop_table("config_version")
    op.drop_table("config_template")
