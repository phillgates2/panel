"""Add performance indexes for better query performance

Revision ID: perf_indexes_001
Revises: dc4e5affd5bc
Create Date: 2025-11-21 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "perf_indexes_001"
down_revision = "dc4e5affd5bc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### Performance indexes for better query performance ###

    # User table indexes
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.create_index("idx_user_email", ["email"], unique=False)
        batch_op.create_index("idx_user_is_active", ["is_active"], unique=False)
        batch_op.create_index(
            "idx_user_is_system_admin", ["is_system_admin"], unique=False
        )
        batch_op.create_index("idx_user_created_at", ["created_at"], unique=False)

    # Server table indexes
    with op.batch_alter_table("server", schema=None) as batch_op:
        batch_op.create_index("idx_server_user_id", ["user_id"], unique=False)
        batch_op.create_index("idx_server_status", ["status"], unique=False)
        batch_op.create_index("idx_server_created_at", ["created_at"], unique=False)
        batch_op.create_index("idx_server_name", ["name"], unique=False)

    # Audit log indexes (critical for performance)
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.create_index("idx_audit_log_user_id", ["user_id"], unique=False)
        batch_op.create_index("idx_audit_log_action", ["action"], unique=False)
        batch_op.create_index("idx_audit_log_created_at", ["created_at"], unique=False)
        batch_op.create_index(
            "idx_audit_log_user_action", ["user_id", "action"], unique=False
        )
        batch_op.create_index("idx_audit_log_timestamp", ["created_at"], unique=False)

    # User session indexes
    with op.batch_alter_table("user_session", schema=None) as batch_op:
        batch_op.create_index("idx_user_session_user_id", ["user_id"], unique=False)
        batch_op.create_index("idx_user_session_token", ["session_token"], unique=True)
        batch_op.create_index("idx_user_session_active", ["is_active"], unique=False)
        batch_op.create_index("idx_user_session_expires", ["expires_at"], unique=False)

    # API key indexes
    with op.batch_alter_table("api_key", schema=None) as batch_op:
        batch_op.create_index("idx_api_key_user_id", ["user_id"], unique=False)
        batch_op.create_index("idx_api_key_prefix", ["key_prefix"], unique=False)

    # Server metrics indexes
    with op.batch_alter_table("server_metrics", schema=None) as batch_op:
        batch_op.create_index(
            "idx_server_metrics_server_id", ["server_id"], unique=False
        )
        batch_op.create_index(
            "idx_server_metrics_timestamp", ["timestamp"], unique=False
        )
        batch_op.create_index("idx_server_metrics_cpu", ["cpu_usage"], unique=False)

    # Player session indexes
    with op.batch_alter_table("player_session", schema=None) as batch_op:
        batch_op.create_index(
            "idx_player_session_server_id", ["server_id"], unique=False
        )
        batch_op.create_index(
            "idx_player_session_player_id", ["player_id"], unique=False
        )
        batch_op.create_index(
            "idx_player_session_start_time", ["start_time"], unique=False
        )
        batch_op.create_index("idx_player_session_end_time", ["end_time"], unique=False)


def downgrade() -> None:
    # ### Drop performance indexes ###

    # Player session indexes
    with op.batch_alter_table("player_session", schema=None) as batch_op:
        batch_op.drop_index("idx_player_session_end_time")
        batch_op.drop_index("idx_player_session_start_time")
        batch_op.drop_index("idx_player_session_player_id")
        batch_op.drop_index("idx_player_session_server_id")

    # Server metrics indexes
    with op.batch_alter_table("server_metrics", schema=None) as batch_op:
        batch_op.drop_index("idx_server_metrics_cpu")
        batch_op.drop_index("idx_server_metrics_timestamp")
        batch_op.drop_index("idx_server_metrics_server_id")

    # API key indexes
    with op.batch_alter_table("api_key", schema=None) as batch_op:
        batch_op.drop_index("idx_api_key_prefix")
        batch_op.drop_index("idx_api_key_user_id")

    # User session indexes
    with op.batch_alter_table("user_session", schema=None) as batch_op:
        batch_op.drop_index("idx_user_session_expires")
        batch_op.drop_index("idx_user_session_active")
        batch_op.drop_index("idx_user_session_token")
        batch_op.drop_index("idx_user_session_user_id")

    # Audit log indexes
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.drop_index("idx_audit_log_timestamp")
        batch_op.drop_index("idx_audit_log_user_action")
        batch_op.drop_index("idx_audit_log_created_at")
        batch_op.drop_index("idx_audit_log_action")
        batch_op.drop_index("idx_audit_log_user_id")

    # Server table indexes
    with op.batch_alter_table("server", schema=None) as batch_op:
        batch_op.drop_index("idx_server_name")
        batch_op.drop_index("idx_server_created_at")
        batch_op.drop_index("idx_server_status")
        batch_op.drop_index("idx_server_user_id")

    # User table indexes
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_index("idx_user_created_at")
        batch_op.drop_index("idx_user_is_system_admin")
        batch_op.drop_index("idx_user_is_active")
        batch_op.drop_index("idx_user_email")
