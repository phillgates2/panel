"""
Celery Application Configuration
Provides asynchronous task processing with Redis backend
"""

from celery import Celery
from flask import Flask

# Create Celery app instance
celery_app = Celery(
    "panel",
    broker="redis://127.0.0.1:6379/0",  # Use same Redis instance
    backend="redis://127.0.0.1:6379/0",
    include=["src.panel.tasks"],  # Include tasks module
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={"retry_policy": {"timeout": 5.0}},
    # Routing (optional)
    task_routes={
        "src.panel.tasks.send_email": {"queue": "email"},
        "src.panel.tasks.process_file": {"queue": "files"},
        "src.panel.tasks.backup_database": {"queue": "maintenance"},
    },
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)


def init_celery(app: Flask) -> Celery:
    """
    Initialize Celery with Flask app context

    Args:
        app: Flask application instance

    Returns:
        Configured Celery app instance
    """
    # Update Celery config from Flask config
    celery_app.conf.update(
        broker_url=app.config.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
        result_backend=app.config.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
    )

    # Create custom task class that provides Flask app context
    class ContextTask(celery_app.Task):
        """Task class that provides Flask app context"""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask

    return celery_app


# Convenience function to get celery app
def get_celery_app() -> Celery:
    """Get the configured Celery app instance"""
    return celery_app
