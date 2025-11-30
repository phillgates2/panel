from flask import render_template
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

def page_not_found(e) -> Tuple[str, int]:
    """Handle 404 errors."""
    logger.warning(f"404 error: {e}")
    return render_template('404.html'), 404

def internal_error(e) -> Tuple[str, int]:
    """Handle 500 errors."""
    logger.error(f"500 error: {e}")
    return render_template('500.html'), 500