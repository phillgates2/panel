"""
Add push notifications support
Revision ID: push_notifications
Revises: oauth_fields
Create Date: 2024-01-01 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "push_notifications"
down_revision = "oauth_fields"
branch_labels = None
depends_on = None


def upgrade():
    """Add push notification tables."""
    op.create_table(
        "notification_subscription",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("subscription_data", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    """Remove push notification tables."""
    op.drop_table("notification_subscription")
