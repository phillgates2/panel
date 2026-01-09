import os

from flask import url_for

from src.panel.config import Config

config = Config()


# Validate required configurations
def validate_config():
    required = ["SECRET_KEY", "SQLALCHEMY_DATABASE_URI"]
    for key in required:
        if not hasattr(config, key) or not getattr(config, key):
            raise ValueError(f"Required config {key} is missing")


validate_config()

# CDN Integration
CDN_ENABLED = os.environ.get("PANEL_CDN_ENABLED", "false").lower() == "true"
CDN_PROVIDER = os.environ.get(
    "PANEL_CDN_PROVIDER", "cloudflare"
)  # cloudflare or cloudfront
CDN_BASE_URL = os.environ.get("PANEL_CDN_BASE_URL", "https://cdn.panel.com")


def get_cdn_url(path):
    """Get CDN URL for static assets"""
    if CDN_ENABLED:
        base = CDN_BASE_URL.rstrip("/")
        return f"{base}/{path.lstrip('/')}"
    return url_for("static", filename=path.lstrip("/"))
