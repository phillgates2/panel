from datetime import datetime, timezone

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, session, url_for)

from app import User, db, verify_csrf
from tools.auth import admin_required as auth_admin_required

cms_bp = Blueprint("cms", __name__, url_prefix="/cms")


@cms_bp.context_processor
def inject_csrf_token():
    """Inject csrf_token function into CMS templates"""
    return {'csrf_token': lambda: session.get('csrf_token', '')}


def admin_required(fn):
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("cms.admin_login", next=request.path))
        return fn(*args, **kwargs)

    wrapped.__name__ = getattr(fn, "__name__", "wrapped")
    return wrapped


class Page(db.Model):
    __tablename__ = "cms_page"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class BlogPost(db.Model):
    __tablename__ = "cms_blog_post"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=True)
    excerpt = db.Column(db.String(500), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    author = db.relationship("User", backref="blog_posts", foreign_keys=[author_id])


@cms_bp.route("/")
def index():
    # pagination
    try:
        page = int(request.args.get("page", 1))
    except Exception:
        page = 1
    per_page = int(current_app.config.get("CMS_PER_PAGE", 10))
    q = db.session.query(Page).order_by(Page.title)
    total = q.count()
    pages = q.offset((page - 1) * per_page).limit(per_page).all()
    return render_template(
        "cms/index.html", pages=pages, page=page, per_page=per_page, total=total
    )


@cms_bp.route("/<slug>")
def view(slug):
    page = db.session.query(Page).filter_by(slug=slug).first()
    if not page:
        abort(404)
    # optional markdown rendering with sanitization
    html_content = None
    try:
        from markdown import markdown as md

        raw_html = md(page.content or "")
        try:
            import bleach

            html_content = bleach.clean(
                raw_html,
                tags=bleach.sanitizer.ALLOWED_TAGS + ["p", "pre", "code"],
                strip=True,
            )
        except Exception:
            # fallback: escape HTML
            from markupsafe import escape

            html_content = escape(raw_html)
    except Exception:
        html_content = page.content
    return render_template("cms/view.html", page=page, html_content=html_content)


@cms_bp.route("/create", methods=["GET", "POST"])
@auth_admin_required
def create():
    if request.method == "POST":
        # CSRF protection
        try:
            verify_csrf()
        except Exception:
            flash("Invalid CSRF token", "error")
            return redirect(url_for("cms.create"))

        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip()
        content = request.form.get("content", "")
        if not title or not slug:
            flash("Title and slug are required", "error")
            return redirect(url_for("cms.create"))
        p = Page(title=title, slug=slug, content=content)
        db.session.add(p)
        db.session.commit()
        flash("Page created", "success")
        return redirect(url_for("cms.view", slug=slug))
    return render_template("cms/create.html")


@cms_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    next_url = request.args.get("next") or url_for("cms.index")
    if request.method == "POST":
        # CSRF protection
        try:
            verify_csrf()
        except Exception:
            flash("Invalid CSRF token", "error")
            return redirect(url_for("cms.admin_login"))

        username = request.form.get("username")
        password = request.form.get("password")

        # Prefer authenticating against the User model (hashed passwords).
        user = None
        try:
            user = (
                db.session.query(User).filter_by(email=(username or "").lower()).first()
            )
        except Exception:
            user = None
        if user:
            if user.check_password(password):
                session["admin_authenticated"] = True
                session["admin_user_id"] = user.id
                flash("Logged in as admin", "success")
                return redirect(next_url)
            flash("Invalid credentials", "error")
            return redirect(url_for("cms.admin_login"))

        # Fallback to config-based credentials (legacy)
        cfg_user = current_app.config.get("ADMIN_USER", "admin")
        cfg_pass = current_app.config.get("ADMIN_PASSWORD", "admin")
        if username == cfg_user and password == cfg_pass:
            session["admin_authenticated"] = True
            flash("Logged in as admin (legacy config)", "success")
            return redirect(next_url)
        flash("Invalid credentials", "error")
    return render_template("cms/admin_login.html", next=next_url)


@cms_bp.route("/admin/logout")
def admin_logout():
    session.pop("admin_authenticated", None)
    session.pop("admin_user_id", None)
    session.pop("user_id", None)
    flash("Logged out", "success")
    return redirect(url_for("cms.index"))


# ==================== Blog Post Management (Admin) ====================


@cms_bp.route("/admin/blog")
@admin_required
def admin_blog_list():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template("cms/admin_blog_list.html", posts=posts)


@cms_bp.route("/admin/blog/new", methods=["GET", "POST"])
@admin_required
def admin_blog_create():
    if request.method == "POST":
        try:
            verify_csrf()
        except Exception:
            flash("Invalid CSRF token", "error")
            return redirect(url_for("cms.admin_blog_create"))
        
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip()
        content = request.form.get("content", "")
        excerpt = request.form.get("excerpt", "").strip()
        is_published = request.form.get("is_published") == "on"
        
        if not title or not slug:
            flash("Title and slug are required", "error")
            return redirect(url_for("cms.admin_blog_create"))
        
        # Check if slug already exists
        existing = BlogPost.query.filter_by(slug=slug).first()
        if existing:
            flash(f"Slug '{slug}' already exists", "error")
            return redirect(url_for("cms.admin_blog_create"))
        
        author_id = session.get("admin_user_id") or session.get("user_id")
        if not author_id:
            flash("Author not found", "error")
            return redirect(url_for("cms.admin_blog_create"))
        
        post = BlogPost(
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            author_id=author_id,
            is_published=is_published
        )
        db.session.add(post)
        db.session.commit()
        flash(f"Blog post '{title}' created", "success")
        return redirect(url_for("cms.admin_blog_list"))
    
    return render_template("cms/admin_blog_edit.html", post=None)


@cms_bp.route("/admin/blog/<int:post_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_blog_edit(post_id):
    post = BlogPost.query.get_or_404(post_id)
    
    if request.method == "POST":
        try:
            verify_csrf()
        except Exception:
            flash("Invalid CSRF token", "error")
            return redirect(url_for("cms.admin_blog_edit", post_id=post_id))
        
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip()
        content = request.form.get("content", "")
        excerpt = request.form.get("excerpt", "").strip()
        is_published = request.form.get("is_published") == "on"
        
        if not title or not slug:
            flash("Title and slug are required", "error")
            return redirect(url_for("cms.admin_blog_edit", post_id=post_id))
        
        # Check if slug conflicts with another post
        existing = BlogPost.query.filter(BlogPost.slug == slug, BlogPost.id != post_id).first()
        if existing:
            flash(f"Slug '{slug}' is already used by another post", "error")
            return redirect(url_for("cms.admin_blog_edit", post_id=post_id))
        
        post.title = title
        post.slug = slug
        post.content = content
        post.excerpt = excerpt
        post.is_published = is_published
        post.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f"Blog post '{title}' updated", "success")
        return redirect(url_for("cms.admin_blog_list"))
    
    return render_template("cms/admin_blog_edit.html", post=post)


@cms_bp.route("/admin/blog/<int:post_id>/delete", methods=["POST"])
@admin_required
def admin_blog_delete(post_id):
    try:
        verify_csrf()
    except Exception:
        flash("Invalid CSRF token", "error")
        return redirect(url_for("cms.admin_blog_list"))
    
    post = BlogPost.query.get_or_404(post_id)
    title = post.title
    db.session.delete(post)
    db.session.commit()
    flash(f"Blog post '{title}' deleted", "success")
    return redirect(url_for("cms.admin_blog_list"))


# ==================== Public Blog Routes ====================


@cms_bp.route("/blog")
def blog_index():
    posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).all()
    return render_template("cms/blog_index.html", posts=posts)


@cms_bp.route("/blog/<slug>")
def blog_post(slug):
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()
    return render_template("cms/blog_post.html", post=post)
