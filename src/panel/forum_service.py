"""Forum service blueprint."""

from flask import Blueprint

forum_bp = Blueprint("forum", __name__)


@forum_bp.route("/")
def index():
    return "Forum index"
