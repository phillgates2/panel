"""
Centralized logging configuration for Panel
Provides structured logging with proper levels and handlers
"""

import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path


def setup_logging(app):
    """Configure logging for the Flask application"""
    
    # Get log level from config or environment
    log_level_name = os.environ.get('LOG_LEVEL', app.config.get('LOG_LEVEL', 'INFO'))
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Create logs directory
    log_dir = Path(app.config.get('LOG_DIR', 'instance/logs'))
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure app logger
    app.logger.setLevel(log_level)
    
    # Remove default handlers
    app.logger.handlers.clear()
    
    # Console handler with color support
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    app.logger.addHandler(console_handler)
    
    # File handler - rotates daily
    file_handler = TimedRotatingFileHandler(
        filename=log_dir / 'panel.log',
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    app.logger.addHandler(file_handler)
    
    # Error file handler - only errors and above
    error_handler = RotatingFileHandler(
        filename=log_dir / 'panel_errors.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    app.logger.addHandler(error_handler)
    
    # Security audit log handler
    if app.config.get('AUDIT_LOG_ENABLED', True):
        audit_dir = Path(app.config.get('AUDIT_LOG_DIR', 'instance/audit_logs'))
        audit_dir.mkdir(parents=True, exist_ok=True)
        
        audit_handler = TimedRotatingFileHandler(
            filename=audit_dir / 'security_audit.log',
            when='midnight',
            interval=1,
            backupCount=365,  # Keep 1 year of audit logs
            encoding='utf-8'
        )
        audit_handler.setLevel(logging.INFO)
        audit_formatter = logging.Formatter(
            '%(asctime)s [AUDIT] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        audit_handler.setFormatter(audit_formatter)
        
        # Create separate logger for audit events
        audit_logger = logging.getLogger('panel.audit')
        audit_logger.setLevel(logging.INFO)
        audit_logger.addHandler(audit_handler)
        audit_logger.propagate = False
    
    # Set SQLAlchemy logging level
    if not app.config.get('SQLALCHEMY_ECHO', False):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Werkzeug logging
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO if app.debug else logging.WARNING)
    
    app.logger.info('Logging configured successfully')
    app.logger.info(f'Log level: {log_level_name}')
    app.logger.info(f'Log directory: {log_dir}')
    
    return app.logger


def get_audit_logger():
    """Get the security audit logger"""
    return logging.getLogger('panel.audit')


def log_security_event(event_type, message, user_id=None, ip_address=None, **kwargs):
    """Log a security event to the audit log"""
    audit_logger = get_audit_logger()
    
    details = {
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': ip_address,
        **kwargs
    }
    
    log_message = f"{message} | {' | '.join(f'{k}={v}' for k, v in details.items() if v is not None)}"
    audit_logger.info(log_message)
