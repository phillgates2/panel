from flask import Blueprint, abort, flash, render_template, request, redirect, url_for, session
from src.panel.models import db, User

cms_bp = Blueprint("cms", __name__, url_prefix="/cms")

@cms_bp.route("/", methods=["GET"], endpoint="index")
def cms_index():
    # Minimal index route returns 200 OK with empty page
    return render_template("cms_index.html")

@cms_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        u = db.session.query(User).filter_by(email=username).first()
        if u and u.check_password(password):
            session["user_id"] = u.id
            from flask import flash
            flash("Logged in", "success")
            return redirect(url_for("main.dashboard"))
        # Always return 200 with login form on failure per minimal CMS
        return render_template("cms_admin_login.html")
    return render_template("cms_admin_login.html")

@cms_bp.route("/admin/blog", methods=["GET"], endpoint="admin_blog_list")
def admin_blog_list():
    # Minimal placeholder for blog management link in dashboard
    return redirect(url_for("main.dashboard"))


@cms_bp.route("/admin/blog/new", methods=["GET", "POST"], endpoint="admin_blog_create")
def admin_blog_create():
    flash("Blog management is not enabled in this build.", "warning")
    return redirect(url_for("cms.admin_blog_list"))


@cms_bp.route(
    "/admin/blog/<int:post_id>/edit", methods=["GET", "POST"], endpoint="admin_blog_edit"
)
def admin_blog_edit(post_id: int):
    flash("Blog management is not enabled in this build.", "warning")
    return redirect(url_for("cms.admin_blog_list"))


@cms_bp.route(
    "/admin/blog/<int:post_id>/delete", methods=["POST"], endpoint="admin_blog_delete"
)
def admin_blog_delete(post_id: int):
    flash("Blog management is not enabled in this build.", "warning")
    return redirect(url_for("cms.admin_blog_list"))

@cms_bp.route("/create", methods=["GET", "POST"], endpoint="create")
def create_page():
    """Minimal CMS page creation.

    Provides endpoints/templates referenced by the UI without requiring the full CMS stack.
    Pages are stored in-memory (per-process) to keep this feature optional.
    """

    if request.method == "GET":
        return render_template("cms/create.html")

    title = (request.form.get("title") or "").strip()
    slug = (request.form.get("slug") or "").strip()
    content = request.form.get("content") or ""

    if not (title and slug):
        flash("Title and slug are required", "error")
        return render_template("cms/create.html"), 400

    from flask import current_app

    pages = current_app.extensions.setdefault("cms_pages", {})
    pages[slug] = {"title": title, "content": content}
    flash("Page created", "success")
    return redirect(url_for("cms.view", slug=slug))

@cms_bp.route("/<slug>", methods=["GET"], endpoint="view")
def view_page(slug: str):
    from flask import current_app
    from types import SimpleNamespace

    pages = current_app.extensions.get("cms_pages", {})
    page = pages.get(slug)
    if not page:
        abort(404)

    page_obj = SimpleNamespace(title=page.get("title"), content=page.get("content"))
    return render_template("cms/view.html", page=page_obj)


@cms_bp.route("/blog", methods=["GET"], endpoint="blog_index")
def blog_index():
    # Minimal public blog index: render with no posts.
    return render_template("cms/blog_index.html", posts=[])


@cms_bp.route("/blog/<slug>", methods=["GET"], endpoint="blog_post")
def blog_post(slug: str):
    # Minimal blog post route. If the full CMS/blog module isn't enabled,
    # return 404 instead of raising errors.
    abort(404)
