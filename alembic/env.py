"""Alembic migration environment configuration."""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import the app and db to access models
try:
    from app import app, db
    
    # Import optional feature modules so their models are registered
    try:
        import cms  # noqa: F401
    except Exception:
        pass
    try:
        import forum  # noqa: F401
    except Exception:
        pass
    
    # Set target metadata from app
    target_metadata = db.metadata
    
    # this is the Alembic Config object
    config = context.config
    
    # Set the SQLAlchemy URL from the app config
    if app.config.get("SQLALCHEMY_DATABASE_URI"):
        config.set_main_option("sqlalchemy.url", app.config["SQLALCHEMY_DATABASE_URI"])
        
except ImportError as e:
    print(f"Warning: Could not import app: {e}")
    config = context.config
    target_metadata = None

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
