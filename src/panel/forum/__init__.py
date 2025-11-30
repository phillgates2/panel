from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app import User, db, verify_csrf

forum_bp = Blueprint("forum", __name__, url_prefix="/forum")


@forum_bp.context_processor
def inject_csrf_token():
    """Inject csrf_token function into forum templates"""
    return {"csrf_token": lambda: session.get("csrf_token", "")}


def get_current_user():
    """Get the currently logged-in user"""
    user_id = session.get("user_id")
    if user_id:
        return db.session.get(User, user_id)
    return None


def is_moderator_or_admin():
    """Check if user is moderator or admin"""
    user = get_current_user()
    if not user:
        return False
    return user.role in ["moderator", "system_admin", "admin"]


def login_required(fn):
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("You must be logged in to perform this action", "error")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)

    wrapped.__name__ = getattr(fn, "__name__", "wrapped")
    return wrapped


def moderator_required(fn):
    def wrapped(*args, **kwargs):
        if not is_moderator_or_admin():
            flash("You must be a moderator or admin to perform this action", "error")
            return redirect(url_for("forum.index"))
        return fn(*args, **kwargs)

    wrapped.__name__ = getattr(fn, "__name__", "wrapped")
    return wrapped


class Thread(db.Model):
    __tablename__ = "forum_thread"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    author = db.relationship("User", backref="forum_threads", foreign_keys=[author_id])

    __table_args__ = (
        db.Index("idx_thread_author", "author_id"),
        db.Index("idx_thread_pinned_created", "is_pinned", "created_at"),
    )


class Post(db.Model):
    __tablename__ = "forum_post"
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("forum_thread.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    thread = db.relationship("Thread", backref="posts")
    author = db.relationship("User", backref="forum_posts", foreign_keys=[author_id])

    __table_args__ = (
        db.Index("idx_post_thread", "thread_id"),
        db.Index("idx_post_author", "author_id"),
        db.Index("idx_post_created", "created_at"),
    )


@forum_bp.route("/")
def index():
    """Public forum index - visible to all"""
    try:
        page = int(request.args.get("page", 1))
    except Exception:
        page = 1
    per_page = int(current_app.config.get("FORUM_PER_PAGE", 10))
    q = db.session.query(Thread).order_by(Thread.is_pinned.desc(), Thread.created_at.desc())
    total = q.count()
    threads = q.offset((page - 1) * per_page).limit(per_page).all()

    # Add post count for each thread
    for thread in threads:
        thread.post_count = len(thread.posts)

    current_user = get_current_user()
    is_mod = is_moderator_or_admin()

    return render_template(
        "forum/index.html",
        threads=threads,
        page=page,
        per_page=per_page,
        total=total,
        current_user=current_user,
        is_moderator=is_mod,
    )


@forum_bp.route("/thread/<int:thread_id>")
def view_thread(thread_id):
    """Public thread view - visible to all"""
    thread = db.session.get(Thread, thread_id)
    if not thread:
        abort(404)

    # paginate replies
    try:
        page = int(request.args.get("page", 1))
    except Exception:
        page = 1
    per_page = int(current_app.config.get("FORUM_REPLIES_PER_PAGE", 20))
    q = db.session.query(Post).filter_by(thread_id=thread_id).order_by(Post.created_at.asc())
    total = q.count()
    posts = q.offset((page - 1) * per_page).limit(per_page).all()

    # optional markdown for posts with sanitization
    try:
        from markdown import markdown as md

        try:
            import bleach

            sanitizer = True
        except Exception:
            sanitizer = False
        for p in posts:
            raw = md(p.content or "")
            if sanitizer:
                p._html = bleach.clean(
                    raw,
                    tags=bleach.sanitizer.ALLOWED_TAGS
                    + ["p", "pre", "code", "h1", "h2", "h3", "ul", "ol", "li", "blockquote"],
                    strip=True,
                )
            else:
                from markupsafe import escape

                p._html = escape(raw)
    except Exception:
        for p in posts:
            from markupsafe import escape

            p._html = escape(p.content)

    current_user = get_current_user()
    is_mod = is_moderator_or_admin()

    return render_template(
        "forum/thread.html",
        thread=thread,
        posts=posts,
        page=page,
        per_page=per_page,
        total=total,
        current_user=current_user,
        is_moderator=is_mod,
    )


@forum_bp.route("/thread/<int:thread_id>/reply", methods=["POST"])
@login_required
def reply_thread(thread_id):
    """Post a reply - requires login"""
    thread = db.session.get(Thread, thread_id)
    if not thread:
        abort(404)

    if thread.is_locked and not is_moderator_or_admin():
        flash("This thread is locked", "error")
        return redirect(url_for("forum.view_thread", thread_id=thread_id))

    # CSRF protection
    try:
        verify_csrf()
    except Exception:
        flash("Invalid CSRF token", "error")
        return redirect(url_for("forum.view_thread", thread_id=thread_id))

    current_user = get_current_user()
    content = request.form.get("content", "").strip()
    if not content:
        flash("Content required", "error")
        return redirect(url_for("forum.view_thread", thread_id=thread_id))

    p = Post(thread_id=thread_id, author_id=current_user.id, content=content)
    db.session.add(p)
    db.session.commit()
    flash("Reply posted", "success")
    return redirect(url_for("forum.view_thread", thread_id=thread_id))


@forum_bp.route("/thread/create", methods=["GET", "POST"])
@login_required
def create_thread():
    """Create a new thread - requires login"""
    if request.method == "POST":
        # CSRF protection
        try:
            verify_csrf()
        except Exception:
            flash("Invalid CSRF token", "error")
            return redirect(url_for("forum.create_thread"))

        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("Title and content required", "error")
            return redirect(url_for("forum.create_thread"))

        current_user = get_current_user()
        t = Thread(title=title, author_id=current_user.id)
        db.session.add(t)
        db.session.flush()
        p = Post(thread_id=t.id, author_id=current_user.id, content=content)
        db.session.add(p)
        db.session.commit()
        flash("Thread created", "success")
        return redirect(url_for("forum.view_thread", thread_id=t.id))

    current_user = get_current_user()
    return render_template("forum/create_thread.html", current_user=current_user)


@forum_bp.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    """Edit post - author or moderator"""
    p = db.session.get(Post, post_id)
    if not p:
        abort(404)

    current_user = get_current_user()
    is_mod = is_moderator_or_admin()

    # Check if user is author or moderator
    if p.author_id != current_user.id and not is_mod:
        flash("You don't have permission to edit this post", "error")
        return redirect(url_for("forum.view_thread", thread_id=p.thread_id))

    if request.method == "POST":
        try:
            verify_csrf()
        except Exception:
            flash("Invalid CSRF token", "error")
            return redirect(url_for("forum.view_thread", thread_id=p.thread_id))
        p.content = request.form.get("content", p.content)
        db.session.commit()
        flash("Post updated", "success")
        return redirect(url_for("forum.view_thread", thread_id=p.thread_id))
    return render_template("forum/edit_post.html", post=p, current_user=current_user)


@forum_bp.route("/post/<int:post_id>/delete", methods=["POST"])
@moderator_required
def delete_post(post_id):
    """Delete post - moderator only"""
    p = db.session.get(Post, post_id)
    if not p:
        abort(404)
    try:
        verify_csrf()
    except Exception:
        flash("Invalid CSRF token", "error")
        return redirect(url_for("forum.view_thread", thread_id=p.thread_id))
    thread_id = p.thread_id
    db.session.delete(p)
    db.session.commit()
    flash("Post deleted", "success")
    return redirect(url_for("forum.view_thread", thread_id=thread_id))


@forum_bp.route("/thread/<int:thread_id>/edit", methods=["GET", "POST"])
@moderator_required
def edit_thread(thread_id):
    """Edit thread - moderator only"""
    t = db.session.get(Thread, thread_id)
    if not t:
        abort(404)
    if request.method == "POST":
        try:
            verify_csrf()
        except Exception:
            flash("Invalid CSRF token", "error")
            return redirect(url_for("forum.view_thread", thread_id=thread_id))
        t.title = request.form.get("title", t.title)
        t.is_pinned = request.form.get("is_pinned") == "on"
        t.is_locked = request.form.get("is_locked") == "on"
        db.session.commit()
        flash("Thread updated", "success")
        return redirect(url_for("forum.view_thread", thread_id=thread_id))

    current_user = get_current_user()
    return render_template("forum/edit_thread.html", thread=t, current_user=current_user)


@forum_bp.route("/thread/<int:thread_id>/delete", methods=["POST"])
@moderator_required
def delete_thread(thread_id):
    """Delete thread - moderator only"""
    t = db.session.get(Thread, thread_id)
    if not t:
        abort(404)
    try:
        verify_csrf()
    except Exception:
        flash("Invalid CSRF token", "error")
        return redirect(url_for("forum.view_thread", thread_id=thread_id))
    # delete posts first
    db.session.query(Post).filter_by(thread_id=thread_id).delete()
    db.session.delete(t)
    db.session.commit()
    flash("Thread deleted", "success")
    return redirect(url_for("forum.index"))


@forum_bp.route("/thread/<int:thread_id>/pin", methods=["POST"])
@moderator_required
def pin_thread(thread_id):
    """Pin/unpin thread - moderator only"""
    t = db.session.get(Thread, thread_id)
    if not t:
        abort(404)
    try:
        verify_csrf()
    except Exception:
        flash("Invalid CSRF token", "error")
        return redirect(url_for("forum.view_thread", thread_id=thread_id))
    t.is_pinned = not t.is_pinned
    db.session.commit()
    flash(f"Thread {'pinned' if t.is_pinned else 'unpinned'}", "success")
    return redirect(url_for("forum.view_thread", thread_id=thread_id))


@forum_bp.route("/thread/<int:thread_id>/lock", methods=["POST"])
@moderator_required
def lock_thread(thread_id):
    """Lock/unlock thread - moderator only"""
    t = db.session.get(Thread, thread_id)
    if not t:
        abort(404)
    try:
        verify_csrf()
    except Exception:
        flash("Invalid CSRF token", "error")
        return redirect(url_for("forum.view_thread", thread_id=thread_id))
    t.is_locked = not t.is_locked
    db.session.commit()
    flash(f"Thread {'locked' if t.is_locked else 'unlocked'}", "success")
    return redirect(url_for("forum.view_thread", thread_id=thread_id))
