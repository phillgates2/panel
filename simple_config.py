"""Simple configuration management for Panel."""


class ValidationError(Exception):
    """Configuration validation error."""

    pass


class PanelConfig:
    """Panel configuration class."""

    def __init__(self):
        self.USE_SQLITE = True
        self.SQLALCHEMY_DATABASE_URI = "sqlite:///panel.db"
        self.TESTING = False
        self.SECRET_KEY = "default-secret-key"


def load_config():
    """Load configuration."""
    return PanelConfig()


def validate_configuration_at_startup(app):
    """Validate configuration at startup."""
    pass
