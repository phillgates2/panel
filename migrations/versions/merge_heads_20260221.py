"""Merge multiple Alembic heads

Revision ID: merge_heads_20260221
Revises: 64c2f8fecc18, ptero_eggs_001, perf_indexes_001, push_notifications, rbac_system_init
Create Date: 2026-02-21

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "merge_heads_20260221"
down_revision = (
    "64c2f8fecc18",
    "ptero_eggs_001",
    "perf_indexes_001",
    "push_notifications",
    "rbac_system_init",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a merge revision; it intentionally performs no schema changes.
    pass


def downgrade() -> None:
    # Downgrading a merge revision is a no-op; Alembic will traverse branches.
    pass
