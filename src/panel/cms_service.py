"""CMS service blueprint."""

from flask import Blueprint

cms_bp = Blueprint("cms", __name__)


@cms_bp.route("/blog")
def blog():
    return "Blog page"
