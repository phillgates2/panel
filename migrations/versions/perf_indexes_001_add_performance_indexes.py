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
    #
    # This migration was historically authored against a richer schema than
    # some deployments have. To avoid breaking fresh installs, we only create
    # an index when its table + required columns exist.

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def _table_exists(table_name: str) -> bool:
        try:
            return table_name in inspector.get_table_names()
        except Exception:
            return False

    def _columns_exist(table_name: str, columns: list[str]) -> bool:
        try:
            existing = {c["name"] for c in inspector.get_columns(table_name)}
        except Exception:
            return False
        return all(col in existing for col in columns)

    def _safe_create_index(index_name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
        if not _table_exists(table_name):
            return
        if not _columns_exist(table_name, columns):
            return
        op.create_index(index_name, table_name, columns, unique=unique)

    # User table indexes
    _safe_create_index("idx_user_email", "user", ["email"], unique=False)
    _safe_create_index("idx_user_is_active", "user", ["is_active"], unique=False)
    _safe_create_index("idx_user_is_system_admin", "user", ["is_system_admin"], unique=False)
    _safe_create_index("idx_user_created_at", "user", ["created_at"], unique=False)

    # Server table indexes
    _safe_create_index("idx_server_user_id", "server", ["user_id"], unique=False)
    _safe_create_index("idx_server_status", "server", ["status"], unique=False)
    _safe_create_index("idx_server_created_at", "server", ["created_at"], unique=False)
    _safe_create_index("idx_server_name", "server", ["name"], unique=False)

    # Audit log indexes
    _safe_create_index("idx_audit_log_user_id", "audit_log", ["user_id"], unique=False)
    _safe_create_index("idx_audit_log_action", "audit_log", ["action"], unique=False)
    _safe_create_index("idx_audit_log_created_at", "audit_log", ["created_at"], unique=False)
    _safe_create_index("idx_audit_log_user_action", "audit_log", ["user_id", "action"], unique=False)
    _safe_create_index("idx_audit_log_timestamp", "audit_log", ["created_at"], unique=False)

    # User session indexes
    _safe_create_index("idx_user_session_user_id", "user_session", ["user_id"], unique=False)
    _safe_create_index("idx_user_session_token", "user_session", ["session_token"], unique=True)
    _safe_create_index("idx_user_session_active", "user_session", ["is_active"], unique=False)
    _safe_create_index("idx_user_session_expires", "user_session", ["expires_at"], unique=False)

    # API key indexes
    _safe_create_index("idx_api_key_user_id", "api_key", ["user_id"], unique=False)
    _safe_create_index("idx_api_key_prefix", "api_key", ["key_prefix"], unique=False)

    # Server metrics indexes
    _safe_create_index("idx_server_metrics_server_id", "server_metrics", ["server_id"], unique=False)
    _safe_create_index("idx_server_metrics_timestamp", "server_metrics", ["timestamp"], unique=False)
    _safe_create_index("idx_server_metrics_cpu", "server_metrics", ["cpu_usage"], unique=False)

    # Player session indexes
    _safe_create_index("idx_player_session_server_id", "player_session", ["server_id"], unique=False)
    _safe_create_index("idx_player_session_player_id", "player_session", ["player_id"], unique=False)
    _safe_create_index("idx_player_session_start_time", "player_session", ["start_time"], unique=False)
    _safe_create_index("idx_player_session_end_time", "player_session", ["end_time"], unique=False)


def downgrade() -> None:
    # ### Drop performance indexes (best-effort) ###
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def _has_index(table_name: str, index_name: str) -> bool:
        try:
            return any(i.get("name") == index_name for i in inspector.get_indexes(table_name))
        except Exception:
            return False

    def _safe_drop_index(index_name: str, table_name: str) -> None:
        if not _has_index(table_name, index_name):
            return
        op.drop_index(index_name, table_name=table_name)

    _safe_drop_index("idx_player_session_end_time", "player_session")
    _safe_drop_index("idx_player_session_start_time", "player_session")
    _safe_drop_index("idx_player_session_player_id", "player_session")
    _safe_drop_index("idx_player_session_server_id", "player_session")

    _safe_drop_index("idx_server_metrics_cpu", "server_metrics")
    _safe_drop_index("idx_server_metrics_timestamp", "server_metrics")
    _safe_drop_index("idx_server_metrics_server_id", "server_metrics")

    _safe_drop_index("idx_api_key_prefix", "api_key")
    _safe_drop_index("idx_api_key_user_id", "api_key")

    _safe_drop_index("idx_user_session_expires", "user_session")
    _safe_drop_index("idx_user_session_active", "user_session")
    _safe_drop_index("idx_user_session_token", "user_session")
    _safe_drop_index("idx_user_session_user_id", "user_session")

    _safe_drop_index("idx_audit_log_timestamp", "audit_log")
    _safe_drop_index("idx_audit_log_user_action", "audit_log")
    _safe_drop_index("idx_audit_log_created_at", "audit_log")
    _safe_drop_index("idx_audit_log_action", "audit_log")
    _safe_drop_index("idx_audit_log_user_id", "audit_log")

    _safe_drop_index("idx_server_name", "server")
    _safe_drop_index("idx_server_created_at", "server")
    _safe_drop_index("idx_server_status", "server")
    _safe_drop_index("idx_server_user_id", "server")

    _safe_drop_index("idx_user_created_at", "user")
    _safe_drop_index("idx_user_is_system_admin", "user")
    _safe_drop_index("idx_user_is_active", "user")
    _safe_drop_index("idx_user_email", "user")
