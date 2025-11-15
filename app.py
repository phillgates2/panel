import os
import time
import io
import secrets
from datetime import datetime, date, timezone
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    flash,
    abort,
)
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask import Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

import config
import subprocess
import os
import redis
from rq import Queue
import tasks
from captcha import generate_captcha_image, generate_captcha_audio
import json
import io
from PIL import Image, ImageOps

app = Flask(__name__)
app.config.from_object(config)
app.secret_key = config.SECRET_KEY

# --- Simple rate limiting helpers (Redis-backed, with in-process fallback) ---
_rl_fallback_store = {}

def _get_redis_conn():
    try:
        redis_url = os.environ.get('PANEL_REDIS_URL', getattr(config, 'REDIS_URL', 'redis://127.0.0.1:6379/0'))
        return redis.from_url(redis_url)
    except Exception:
        return None

def _client_ip():
    # basic client IP detection; behind proxies you could trust X-Forwarded-For
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        return xff.split(',')[0].strip()
    return request.remote_addr or 'unknown'

def rate_limit(action: str, limit: int, window_seconds: int) -> bool:
    """Return True if request allowed, False if rate-limited.
    Skips when TESTING mode is enabled.
    """
    if app.config.get('TESTING', False):
        return True
    ip = _client_ip()
    key = f"rl:{action}:{ip}"
    now = int(time.time())
    rconn = _get_redis_conn()
    if rconn is not None:
        try:
            count = rconn.incr(key)
            if count == 1:
                rconn.expire(key, window_seconds)
            return count <= limit
        except Exception:
            pass
    # Fallback in-process store
    bucket = _rl_fallback_store.get(key)
    if not bucket:
        bucket = {"start": now, "count": 0}
        _rl_fallback_store[key] = bucket
    # reset window if expired
    if now - bucket["start"] >= window_seconds:
        bucket["start"] = now
        bucket["count"] = 0
    bucket["count"] += 1
    return bucket["count"] <= limit

@app.context_processor
def inject_user():
    """Inject `logged_in` and `current_user` into templates.
    Uses `session['user_id']` when present. Returns a simple boolean
    and the `User` instance (or None).
    """
    user = None
    user_id = session.get('user_id')
    if user_id:
        try:
            user = db.session.get(User, user_id)
        except Exception:
            user = None
    # theme enabled flag stored in DB (fallback to instance file if DB empty)
    theme_enabled = False
    try:
        s = db.session.query(SiteSetting).filter_by(key='theme_enabled').first()
        if s and s.value is not None:
            theme_enabled = (s.value.strip() == '1')
        else:
            # fallback to instance file for older installations
            theme_flag = os.path.join(app.root_path, 'instance', 'theme_enabled')
            if os.path.exists(theme_flag):
                with open(theme_flag, 'r', encoding='utf-8') as f:
                    v = f.read().strip()
                    theme_enabled = (v == '1')
    except Exception:
        theme_enabled = False

    return dict(logged_in=bool(user), current_user=user, theme_enabled=theme_enabled, config=app.config)

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    dob = db.Column(db.Date, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    reset_token = db.Column(db.String(128), nullable=True)
    role = db.Column(db.String(32), default='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_system_admin(self):
        return (self.role == 'system_admin') or (self.email.lower() in getattr(config, 'ADMIN_EMAILS', []))

    def is_server_admin(self):
        return self.role == 'server_admin'

    def is_server_mod(self):
        return self.role == 'server_mod'


# Association table: server-specific roles for users (server_admin/server_mod)
class ServerUser(db.Model):
    __tablename__ = 'server_user'
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(32), nullable=False)  # 'server_admin' or 'server_mod'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(512), nullable=True)
    variables_json = db.Column(db.Text, nullable=True)  # structured variables (JSON)
    raw_config = db.Column(db.Text, nullable=True)  # raw server config
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    users = db.relationship('ServerUser', backref='server', cascade='all, delete-orphan')


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(1024), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class SiteSetting(db.Model):
        """Simple key/value storage for site-wide settings.

        Keys used:
            - 'custom_theme_css' : text containing CSS
            - 'theme_enabled' : '1' or '0'
        """
        id = db.Column(db.Integer, primary_key=True)
        key = db.Column(db.String(128), unique=True, nullable=False)
        value = db.Column(db.Text, nullable=True)


class SiteAsset(db.Model):
        """Store uploaded theme assets (logos) in DB when configured.

        Fields:
            - filename: sanitized filename used in URL
            - data: binary blob
            - mimetype: original/derived mimetype
            - created_at
        """
        id = db.Column(db.Integer, primary_key=True)
        filename = db.Column(db.String(256), unique=True, nullable=False)
        data = db.Column(db.LargeBinary, nullable=False)
        mimetype = db.Column(db.String(128), nullable=True)
        created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


def is_admin_user(user):
    return is_system_admin_user(user)


def user_server_role(user, server):
    if not user or not server:
        return None
    if user.is_system_admin():
        return 'system_admin'
    su = ServerUser.query.filter_by(user_id=user.id, server_id=server.id).first()
    if su:
        return su.role
    return None


def user_can_edit_server(user, server):
    # system admins, server_admins and server_mods (for editing) can edit server
    role = user_server_role(user, server)
    if role in ('system_admin', 'server_admin', 'server_mod'):
        return True
    return False


def ensure_csrf():
    # ensure a CSRF token in session for forms
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)

def verify_csrf():
    token = session.get('csrf_token')
    form = request.form.get('csrf_token')
    if not token or not form or token != form:
        abort(400, 'Invalid CSRF token')


# Use after_request instead to avoid session locking issues
@app.after_request
def ensure_csrf_after(response):
    # ensure a CSRF token in session for forms
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return response


@app.context_processor
def ensure_csrf_for_templates():
    # Ensure a CSRF token exists before templates render so forms include it.
    # This is safer than relying on after_request for form rendering in tests
    # and for real browsers which expect the token in the HTML form.
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # CSRF check
        try:
            verify_csrf()
        except Exception:
            flash("Invalid CSRF token", "error")
            return redirect(url_for("register"))
        first = request.form.get("first_name", "").strip()
        last = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        dob_raw = request.form.get("dob", "")
        password = request.form.get("password", "")
        captcha = request.form.get("captcha", "")

        # captcha verify
        if session.get("captcha_text") != captcha:
            flash("Invalid captcha", "error")
            return redirect(url_for("register"))

        # basic validation
        try:
            dob = datetime.strptime(dob_raw, "%Y-%m-%d").date()
        except Exception:
            flash("Invalid date of birth format", "error")
            return redirect(url_for("register"))

        # age check >= 16
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 16:
            flash("You must be at least 16 years old to register", "error")
            return redirect(url_for("register"))

        # password constraints (server-side)
        import re

        if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"\d", password) or not re.search(r"[^A-Za-z0-9]", password):
            flash("Password does not meet complexity requirements", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "error")
            return redirect(url_for("register"))

        user = User(first_name=first, last_name=last, email=email, dob=dob)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful — you can now log in", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/captcha.png")
def captcha_image():
    # generate image and store the expected text in session
    text = generate_captcha_image()
    session["captcha_text"] = text
    session["captcha_ts"] = int(time.time())
    # retrieve last generated image bytes from captcha module
    from captcha import last_image_bytes
    img = last_image_bytes()
    if img:
        # rate limit captcha image generation to avoid abuse
        if not rate_limit('captcha_img', limit=60, window_seconds=60):
            return ("Too Many Requests", 429)
        return send_file(io.BytesIO(img), mimetype="image/png")
    return ("", 404)


@app.route("/captcha_audio")
def captcha_audio():
    # If no captcha in session, regenerate
    text = session.get("captcha_text") or generate_captcha_image()
    session["captcha_text"] = text
    wav_bytes = generate_captcha_audio(text)
    return send_file(io.BytesIO(wav_bytes), mimetype="audio/wav")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            verify_csrf()
        except Exception:
            flash("Invalid CSRF token", "error")
            return redirect(url_for("login"))
        # Rate limit login attempts per IP
        if not rate_limit('login_post', limit=10, window_seconds=300):
            flash("Too many login attempts. Please try again later.", "error")
            return redirect(url_for("login"))
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        captcha = request.form.get("captcha", "")
        # captcha verify (if present and not in testing mode)
        if not app.config.get('TESTING', False):
            # captcha expiry: 3 minutes
            ts = session.get("captcha_ts")
            if not ts or (int(time.time()) - int(ts) > 180):
                flash("Captcha expired. Please refresh and try again.", "error")
                return redirect(url_for("login"))
            if session.get("captcha_text") != captcha:
                flash("Invalid captcha", "error")
                return redirect(url_for("login"))
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            # clear captcha on success
            session.pop("captcha_text", None)
            session.pop("captcha_ts", None)
            flash("Logged in", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "error")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        try:
            verify_csrf()
        except Exception:
            flash("Invalid CSRF token", "error")
            return redirect(url_for("forgot"))
        # Rate limit forgot requests per IP
        if not rate_limit('forgot_post', limit=5, window_seconds=600):
            flash("Too many reset requests. Please try again later.", "error")
            return redirect(url_for("forgot"))
        # Captcha validation (skip in TESTING mode)
        captcha = request.form.get("captcha", "")
        if not app.config.get('TESTING', False):
            ts = session.get("captcha_ts")
            if not ts or (int(time.time()) - int(ts) > 180):
                flash("Captcha expired. Please refresh and try again.", "error")
                return redirect(url_for("forgot"))
            if session.get("captcha_text") != captcha:
                flash("Invalid captcha", "error")
                return redirect(url_for("forgot"))
        email = request.form.get("email", "").lower().strip()
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("If this email exists in our system, a local reset link will be shown.", "info")
            return redirect(url_for("forgot"))
        # create local reset token and show to user (no email sending)
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        db.session.commit()
        # clear captcha on success
        session.pop("captcha_text", None)
        session.pop("captcha_ts", None)
        # Display the token / local link so the admin/user can use it locally
        reset_link = url_for("reset_password", token=token, _external=True)
        return render_template("forgot_local.html", reset_link=reset_link, token=token)
    return render_template("forgot.html")


@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        flash("Invalid or expired token", "error")
        return redirect(url_for("forgot"))
    if request.method == "POST":
        try:
            verify_csrf()
        except Exception:
            flash("Invalid CSRF token", "error")
            return redirect(url_for("reset_password", token=token))
        # Rate limit reset password attempts per IP
        if not rate_limit('reset_post', limit=10, window_seconds=600):
            flash("Too many reset attempts. Please try again later.", "error")
            return redirect(url_for("reset_password", token=token))
        captcha = request.form.get("captcha", "")
        # captcha verify (if not in testing mode)
        if not app.config.get('TESTING', False):
            ts = session.get("captcha_ts")
            if not ts or (int(time.time()) - int(ts) > 180):
                flash("Captcha expired. Please refresh and try again.", "error")
                return redirect(url_for("reset_password", token=token))
            if session.get("captcha_text") != captcha:
                flash("Invalid captcha", "error")
                return redirect(url_for("reset_password", token=token))
        password = request.form.get("password", "")
        import re
        if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"\d", password) or not re.search(r"[^A-Za-z0-9]", password):
            flash("Password does not meet complexity requirements", "error")
            return redirect(url_for("reset_password", token=token))
        user.set_password(password)
        user.reset_token = None
        db.session.commit()
        # clear captcha on success
        session.pop("captcha_text", None)
        session.pop("captcha_ts", None)
        flash("Password reset successful", "success")
        return redirect(url_for("login"))
    return render_template("reset.html", token=token)


@app.route("/dashboard")
def dashboard():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    return render_template("dashboard.html", user=user, config=config)


@app.route('/rcon', methods=['GET', 'POST'])
def rcon_console():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    output = None
    if request.method == 'POST':
        try:
            verify_csrf()
        except Exception:
            flash('Invalid CSRF token', 'error')
            return redirect(url_for('rcon_console'))
        cmd = request.form.get('command', '').strip()
        if cmd:
            from rcon_client import ETLegacyRcon
            rc = ETLegacyRcon()
            try:
                output = rc.send(cmd)
            except Exception as e:
                output = f'Error: {e}'
    return render_template('rcon.html', output=output)


def is_system_admin_user(user):
    if not user or not user.email:
        return False
    return user.is_system_admin()

def is_server_admin_user(user):
    if not user or not user.email:
        return False
    return user.is_server_admin()


def is_server_mod_user(user):
    if not user or not user.email:
        return False
    return user.is_server_mod()


@app.route('/admin/tools', methods=['GET'])
def admin_tools():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    if not is_system_admin_user(user):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))

    # Attempt to read logs from configured log dir, fallback to journalctl
    memwatch_log = ''
    autodeploy_log = ''
    log_dir = getattr(config, 'LOG_DIR', '/var/log/panel')
    mem_file = os.path.join(log_dir, 'memwatch.log')
    auto_file = os.path.join(log_dir, 'autodeploy.log')
    try:
        if os.path.exists(mem_file):
            with open(mem_file, 'r') as f:
                memwatch_log = ''.join(f.readlines()[-400:])
        else:
            memwatch_log = subprocess.run(['journalctl','-u','memwatch.service','-n','200','--no-pager'], capture_output=True, text=True).stdout
    except Exception as e:
        memwatch_log = f'Could not read memwatch log: {e}'

    try:
        if os.path.exists(auto_file):
            with open(auto_file, 'r') as f:
                autodeploy_log = ''.join(f.readlines()[-400:])
        else:
            autodeploy_log = subprocess.run(['journalctl','-u','autodeploy.service','-n','200','--no-pager'], capture_output=True, text=True).stdout
    except Exception as e:
        autodeploy_log = f'Could not read autodeploy log: {e}'

    return render_template('admin_tools.html', memwatch_log=memwatch_log, autodeploy_log=autodeploy_log)


def _migrate_theme_into_db():
    """Migration helper: import existing static CSS and instance flag into DB if missing.

    This runs at first request to ensure it executes under WSGI servers too.
    """
    try:
        s_css = SiteSetting.query.filter_by(key='custom_theme_css').first()
        theme_path = os.path.join(app.root_path, 'static', 'css', 'custom_theme.css')
        if not s_css and os.path.exists(theme_path):
            with open(theme_path, 'r', encoding='utf-8') as f:
                css = f.read()
            s_css = SiteSetting(key='custom_theme_css', value=css)
            db.session.add(s_css)

        s_flag = SiteSetting.query.filter_by(key='theme_enabled').first()
        flag_path = os.path.join(app.root_path, 'instance', 'theme_enabled')
        if not s_flag and os.path.exists(flag_path):
            try:
                with open(flag_path, 'r', encoding='utf-8') as f:
                    v = f.read().strip()
                s_flag = SiteSetting(key='theme_enabled', value=('1' if v == '1' else '0'))
                db.session.add(s_flag)
            except Exception:
                pass

        if (s_css or s_flag):
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


@app.before_request
def ensure_theme_migration_once():
    # Run migration once before handling the first request. Uses a module-level
    # flag to avoid repeated work and is safe under WSGI servers.
    if getattr(app, '_theme_migrated', False):
        return
    try:
        db.create_all()
    except Exception:
        pass
    _migrate_theme_into_db()
    app._theme_migrated = True


@app.route('/theme.css')
def theme_css():
    """Serve the custom theme CSS from the DB dynamically.

    Returns an empty response (200, text/css) when no CSS stored.
    """
    try:
        s_css = SiteSetting.query.filter_by(key='custom_theme_css').first()
        css = s_css.value if (s_css and s_css.value) else ''
    except Exception:
        css = ''
    return Response(css, mimetype='text/css')


@app.route('/theme_asset/<path:filename>')
def theme_asset(filename):
    # Deprecated filename-based route: try to find by filename (filesystem or DB)
    assets_dir = os.path.join(app.root_path, 'instance', 'theme_assets')
    safe = secure_filename(filename)
    file_path = os.path.join(assets_dir, safe)
    if os.path.exists(file_path):
        return send_file(file_path)
    sa = SiteAsset.query.filter_by(filename=safe).first()
    if sa:
        return Response(sa.data, mimetype=sa.mimetype or 'application/octet-stream')
    abort(404)


@app.route('/theme_asset/id/<int:asset_id>')
def theme_asset_by_id(asset_id):
    # Serve asset by DB id (preferred)
    sa = db.session.get(SiteAsset, asset_id)
    if sa:
        return Response(sa.data, mimetype=sa.mimetype or 'application/octet-stream')
    # fallback to filesystem with name equal to id (unlikely)
    abort(404)


@app.route('/theme_asset/thumb/<int:asset_id>')
def theme_asset_thumb(asset_id):
    # produce a small thumbnail (PNG) for the asset
    sa = db.session.get(SiteAsset, asset_id)
    if not sa:
        abort(404)
    try:
        img = Image.open(io.BytesIO(sa.data))
        img = ImageOps.exif_transpose(img)
        img.thumbnail((128,128))
        out = io.BytesIO()
        # serve thumbnail as PNG for broad support
        img.save(out, format='PNG')
        out.seek(0)
        return Response(out.read(), mimetype='image/png')
    except Exception:
        abort(404)


@app.route('/admin/theme', methods=['GET', 'POST'])
def admin_theme():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    if not is_system_admin_user(user):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))

    theme_path = os.path.join(app.root_path, 'static', 'css', 'custom_theme.css')
    if request.method == 'POST':
        try:
            verify_csrf()
        except Exception:
            flash('Invalid CSRF token', 'error')
            return redirect(url_for('admin_theme'))
        # handle file upload when upload=1 query param present
        if request.args.get('upload') == '1' and 'logo' in request.files:
            f: FileStorage = request.files.get('logo')
            if f and f.filename:
                filename = secure_filename(f.filename)
                # read file bytes for validation and storage
                try:
                    data = f.read()
                except Exception as e:
                    flash(f'Error reading uploaded file: {e}', 'error')
                    return redirect(url_for('admin_theme'))

                # validation: size
                max_bytes = app.config.get('THEME_UPLOAD_MAX_BYTES', getattr(config, 'THEME_UPLOAD_MAX_BYTES', 1_048_576))
                if len(data) > max_bytes:
                    flash(f'File too large (max {max_bytes} bytes)', 'error')
                    return redirect(url_for('admin_theme'))

                # validation: mime/type detection using Pillow (or SVG quick-check)
                mimetype = f.mimetype or ''
                allowed_mimes = app.config.get('THEME_ALLOWED_MIMES', getattr(config, 'THEME_ALLOWED_MIMES', 'image/png,image/jpeg,image/gif,image/webp,image/svg+xml')).split(',')
                is_svg = False
                try:
                    head = data[:512].lstrip()
                    if head.startswith(b"<") and (b"<svg" in head.lower() or b"<?xml" in head.lower()):
                        is_svg = True
                except Exception:
                    is_svg = False

                effective_mime = None
                processed_bytes = data
                # If SVG, accept if allowed
                if is_svg:
                    effective_mime = 'image/svg+xml'
                else:
                    # Try opening with Pillow
                    try:
                        img = Image.open(io.BytesIO(data))
                        fmt = (img.format or '').upper()
                        if not fmt:
                            raise Exception('Unknown image format')
                        img = ImageOps.exif_transpose(img)

                        # optional resize / normalization
                        max_w = app.config.get('THEME_MAX_WIDTH', getattr(config, 'THEME_MAX_WIDTH', 2048))
                        max_h = app.config.get('THEME_MAX_HEIGHT', getattr(config, 'THEME_MAX_HEIGHT', 2048))
                        if img.width > max_w or img.height > max_h:
                            img.thumbnail((max_w, max_h))

                        # normalize mode for JPEG
                        out_io = io.BytesIO()
                        # Normalize everything to PNG for thumbnails/logos to avoid
                        # format-specific save issues and ensure broad browser support.
                        if img.mode in ('RGBA', 'LA'):
                            out = img
                        else:
                            out = img.convert('RGBA')
                        out.save(out_io, format='PNG')
                        processed_bytes = out_io.getvalue()
                        effective_mime = 'image/png'
                    except Exception as e:
                        import traceback
                        tb = traceback.format_exc()
                        try:
                            app.logger.error("Theme image processing error: %s\n%s", e, tb)
                        except Exception:
                            print("Theme image processing error:", e)
                            print(tb)
                        flash(f'Could not process uploaded image: {e}', 'error')
                        return redirect(url_for('admin_theme'))

                if effective_mime not in allowed_mimes:
                    flash(f'Invalid file type: {effective_mime}', 'error')
                    return redirect(url_for('admin_theme'))

                # store either in DB or filesystem
                store_in_db = app.config.get('THEME_STORE_IN_DB', getattr(config, 'THEME_STORE_IN_DB', False))
                try:
                    if store_in_db:
                        # upsert by filename
                        sa = SiteAsset.query.filter_by(filename=filename).first()
                        if not sa:
                            sa = SiteAsset(filename=filename, data=processed_bytes, mimetype=effective_mime)
                        else:
                            sa.data = processed_bytes
                            sa.mimetype = effective_mime
                        db.session.add(sa)
                        db.session.commit()
                    else:
                        assets_dir = os.path.join(app.root_path, 'instance', 'theme_assets')
                        os.makedirs(assets_dir, exist_ok=True)
                        save_path = os.path.join(assets_dir, filename)
                        with open(save_path, 'wb') as wf:
                            wf.write(processed_bytes)
                    flash(f'Logo uploaded: {filename}', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error saving logo: {e}', 'error')
            return redirect(url_for('admin_theme'))
        # handle delete logo
        # single delete via asset id
        if request.form.get('delete_asset_id'):
            try:
                aid = int(request.form.get('delete_asset_id'))
            except Exception:
                aid = None
            if aid:
                try:
                    sa = db.session.get(SiteAsset, aid)
                    if sa:
                        # remove filesystem copy if exists
                        assets_dir = os.path.join(app.root_path, 'instance', 'theme_assets')
                        fs_path = os.path.join(assets_dir, sa.filename)
                        if os.path.exists(fs_path):
                            os.remove(fs_path)
                        db.session.delete(sa)
                        db.session.commit()
                        flash(f'Deleted logo id={aid}', 'success')
                    else:
                        flash('Asset not found', 'error')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error deleting asset: {e}', 'error')
            return redirect(url_for('admin_theme'))

        # bulk delete
        if request.args.get('bulk_delete') == '1' and request.form.getlist('asset_ids'):
            ids = request.form.getlist('asset_ids')
            deleted = 0
            for sid in ids:
                try:
                    aid = int(sid)
                except Exception:
                    continue
                sa = db.session.get(SiteAsset, aid)
                try:
                    if sa:
                        assets_dir = os.path.join(app.root_path, 'instance', 'theme_assets')
                        fs_path = os.path.join(assets_dir, sa.filename)
                        if os.path.exists(fs_path):
                            os.remove(fs_path)
                        db.session.delete(sa)
                        deleted += 1
                except Exception:
                    db.session.rollback()
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            flash(f'Deleted {deleted} assets', 'success')
            return redirect(url_for('admin_theme'))
        css = request.form.get('css', '')
        # handle theme enabled toggle
        enabled = request.form.get('enabled') == '1'
        try:
            # persist to DB (upsert)
            s_css = SiteSetting.query.filter_by(key='custom_theme_css').first()
            if not s_css:
                s_css = SiteSetting(key='custom_theme_css', value=css)
            else:
                s_css.value = css
            s_flag = SiteSetting.query.filter_by(key='theme_enabled').first()
            if not s_flag:
                s_flag = SiteSetting(key='theme_enabled', value=('1' if enabled else '0'))
            else:
                s_flag.value = ('1' if enabled else '0')
            db.session.add(s_css)
            db.session.add(s_flag)
            db.session.commit()

            flash('Theme saved', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving theme: {e}', 'error')
        return redirect(url_for('admin_theme'))

    # handle listing/uploading logos
    assets = []
    try:
        # list DB-stored assets
        assets = SiteAsset.query.order_by(SiteAsset.created_at.desc()).all()
    except Exception:
        assets = []

    css = ''
    try:
        # prefer DB-stored CSS
        s_css = SiteSetting.query.filter_by(key='custom_theme_css').first()
        if s_css and s_css.value is not None:
            css = s_css.value
        else:
            # fallback: try to read existing static file (migration path)
            if os.path.exists(theme_path):
                with open(theme_path, 'r', encoding='utf-8') as f:
                    css = f.read()
    except Exception as e:
        flash(f'Error reading theme file or DB: {e}', 'error')

    return render_template('admin_theme.html', css=css, assets=assets)


@app.route('/admin/users/role', methods=['POST'])
def admin_set_role():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    actor = db.session.get(User, uid)
    if not is_system_admin_user(actor):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    try:
        verify_csrf()
    except Exception:
        flash('Invalid CSRF token', 'error')
        return redirect(url_for('admin_users'))
    user_id = request.form.get('user_id')
    new_role = request.form.get('role')
    u = db.session.get(User, int(user_id)) if user_id else None
    if not u:
        flash('User not found', 'error')
        return redirect(url_for('admin_users'))
    old = u.role
    u.role = new_role
    db.session.add(AuditLog(actor_id=actor.id, action=f"changed_role:{u.email}:{old}->{new_role}"))
    db.session.commit()
    flash('Role updated', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/servers', methods=['GET'])
def admin_servers():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    if not is_system_admin_user(user):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    servers = Server.query.order_by(Server.name).all()
    return render_template('admin_servers.html', servers=servers)


@app.route('/admin/servers/create', methods=['GET', 'POST'])
def admin_create_server():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    actor = db.session.get(User, uid)
    if not is_system_admin_user(actor):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        try:
            verify_csrf()
        except Exception:
            flash('Invalid CSRF token', 'error')
            return redirect(url_for('admin_create_server'))
        name = request.form.get('name', '').strip()
        desc = request.form.get('description', '').strip()
        if not name:
            flash('Name is required', 'error')
            return redirect(url_for('admin_create_server'))
        if Server.query.filter_by(name=name).first():
            flash('Server name already exists', 'error')
            return redirect(url_for('admin_create_server'))
        # create server with default config and assign creator as server_admin
        default_vars = {'max_players': 16, 'map': 'default', 'motd': 'Welcome'}
        s = Server(name=name, description=desc, variables_json=json.dumps(default_vars, indent=2), raw_config='# default config\n')
        db.session.add(s)
        db.session.commit()
        # after commit, create mapping for actor as server_admin
        su = ServerUser(server_id=s.id, user_id=actor.id, role='server_admin')
        db.session.add(su)
        db.session.add(AuditLog(actor_id=actor.id, action=f'create_server:{name}'))
        db.session.commit()
        flash('Server created', 'success')
        return redirect(url_for('admin_servers'))
    return render_template('server_create.html')


@app.route('/admin/servers/<int:server_id>/delete', methods=['POST'])
def admin_delete_server(server_id):
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    actor = db.session.get(User, uid)
    if not is_system_admin_user(actor):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    try:
        verify_csrf()
    except Exception:
        flash('Invalid CSRF token', 'error')
        return redirect(url_for('admin_servers'))
    s = db.session.get(Server, server_id)
    if not s:
        flash('Server not found', 'error')
        return redirect(url_for('admin_servers'))
    name = s.name
    db.session.delete(s)
    db.session.add(AuditLog(actor_id=actor.id, action=f'delete_server:{name}'))
    db.session.commit()
    flash('Server deleted', 'success')
    return redirect(url_for('admin_servers'))


@app.route('/admin/audit', methods=['GET'])
def admin_audit():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    if not is_system_admin_user(user):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    # pagination & filtering
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    actor_filter = request.args.get('actor')
    action_filter = request.args.get('action')
    q = AuditLog.query
    if actor_filter:
        # try to resolve actor id by email
        a_user = User.query.filter_by(email=actor_filter.lower()).first()
        if a_user:
            q = q.filter(AuditLog.actor_id == a_user.id)
        else:
            q = q.filter(AuditLog.action.contains(actor_filter))
    if action_filter:
        q = q.filter(AuditLog.action.contains(action_filter))
    total = q.count()
    entries = q.order_by(AuditLog.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()
    resolved = []
    for e in entries:
        actor = db.session.get(User, e.actor_id) if e.actor_id else None
        resolved.append({'id': e.id, 'actor': actor.email if actor else None, 'action': e.action, 'ts': e.created_at})
    return render_template('admin_audit.html', entries=resolved, page=page, per_page=per_page, total=total, actor_filter=actor_filter or '', action_filter=action_filter or '')



@app.route('/admin/audit/export', methods=['GET'])
def admin_audit_export():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    if not is_system_admin_user(user):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    actor_filter = request.args.get('actor')
    action_filter = request.args.get('action')
    # Build raw SQL query with filters
    sql = "SELECT audit_log.id, audit_log.created_at, user.email, audit_log.action FROM audit_log LEFT JOIN user ON audit_log.actor_id = user.id WHERE 1=1"
    params = []
    if actor_filter:
        # resolve actor email
        a_user = db.session.query(User).filter_by(email=actor_filter.lower()).first()
        if a_user:
            sql += " AND audit_log.actor_id = %s"
            params.append(a_user.id)
        else:
            sql += " AND audit_log.action LIKE %s"
            params.append(f'%{actor_filter}%')
    if action_filter:
        sql += " AND audit_log.action LIKE %s"
        params.append(f'%{action_filter}%')
    sql += " ORDER BY audit_log.created_at DESC"
    # stream CSV using raw SQL cursor
    def generate():
        import csv
        from io import StringIO
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(['id','timestamp','actor','action'])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        # use raw connection cursor to avoid ORM overhead
        with db.engine.connect() as conn:
            result = conn.execute(db.text(sql), params)
            for row in result:
                audit_id, ts, actor_email, action = row
                ts_str = ''
                if ts:
                    # handle both datetime objects and string timestamps (SQLite returns strings)
                    ts_str = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
                writer.writerow([audit_id, ts_str, actor_email or '', action])
                yield buf.getvalue()
                buf.seek(0)
                buf.truncate(0)

    from flask import Response
    headers = {
        'Content-Disposition': 'attachment; filename="audit.csv"'
    }
    return Response(generate(), mimetype='text/csv', headers=headers)


@app.route('/admin/users', methods=['GET'])
def admin_users():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    if not is_system_admin_user(user):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    users = User.query.order_by(User.email).all()
    return render_template('admin_users.html', users=users)


@app.route('/server/<int:server_id>', methods=['GET', 'POST'])
def server_edit(server_id):
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    server = db.session.get(Server, server_id)
    if not server:
        flash('Server not found', 'error')
        return redirect(url_for('dashboard'))
    if not user_can_edit_server(user, server):
        flash('Insufficient privileges for this server', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        try:
            verify_csrf()
        except Exception:
            flash('Invalid CSRF token', 'error')
            return redirect(url_for('server_edit', server_id=server_id))
        # accept either structured JSON variables or raw config
        vars_text = request.form.get('variables_json', '').strip()
        raw_cfg = request.form.get('raw_config', '')
        if vars_text:
            try:
                parsed = json.loads(vars_text)
                # store pretty-printed JSON
                server.variables_json = json.dumps(parsed, indent=2)
            except Exception as e:
                flash(f'Invalid JSON: {e}', 'error')
                return redirect(url_for('server_edit', server_id=server_id))
        server.raw_config = raw_cfg
        db.session.add(AuditLog(actor_id=user.id, action=f'edit_server:{server.name}'))
        db.session.commit()
        flash('Server updated', 'success')
        return redirect(url_for('server_edit', server_id=server_id))
    # GET
    return render_template('server_edit.html', server=server, user=user)


@app.route('/admin/server/<int:server_id>/manage_users', methods=['GET', 'POST'])
def admin_server_manage_users(server_id):
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    actor = db.session.get(User, uid)
    if not is_system_admin_user(actor):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    server = db.session.get(Server, server_id)
    if not server:
        flash('Server not found', 'error')
        return redirect(url_for('admin_servers'))
    if request.method == 'POST':
        try:
            verify_csrf()
        except Exception:
            flash('Invalid CSRF token', 'error')
            return redirect(url_for('admin_server_manage_users', server_id=server_id))
        # expected form inputs: user_<id> = role or empty
        users = User.query.order_by(User.email).all()
        # remove existing mappings
        ServerUser.query.filter_by(server_id=server.id).delete()
        for u in users:
            key = f'user_{u.id}'
            role = request.form.get(key)
            if role in ('server_admin', 'server_mod'):
                su = ServerUser(server_id=server.id, user_id=u.id, role=role)
                db.session.add(su)
                db.session.add(AuditLog(actor_id=actor.id, action=f'assign_server_role:{server.name}:{u.email}->{role}'))
        db.session.commit()
        flash('Server user assignments updated', 'success')
        return redirect(url_for('admin_server_manage_users', server_id=server_id))

    users = User.query.order_by(User.email).all()
    assignments = {su.user_id: su.role for su in server.users}
    return render_template('admin_server_manage.html', server=server, users=users, assignments=assignments)


@app.route('/admin/jobs', methods=['GET'])
def admin_jobs():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    if not is_admin_user(user):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))

    # Pagination and filtering
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    status_filter = request.args.get('status')  # queued, started, finished, failed
    func_filter = request.args.get('func')
    try:
        redis_url = os.environ.get('PANEL_REDIS_URL', config.REDIS_URL)
        rconn = redis.from_url(redis_url)
        q = Queue('default', connection=rconn)
        all_jobs = q.jobs  # note: returns all jobs in memory
        # optional filtering
        if status_filter:
            all_jobs = [j for j in all_jobs if j.get_status() == status_filter]
        if func_filter:
            all_jobs = [j for j in all_jobs if getattr(j, 'func_name', '').find(func_filter) != -1]
        total = len(all_jobs)
        # pagination
        start = (page - 1) * per_page
        end = start + per_page
        jobs = all_jobs[start:end]
    except Exception as e:
        flash(f'Could not read queue: {e}', 'error')
        jobs = []
        total = 0

    return render_template('admin_jobs.html', jobs=jobs, page=page, per_page=per_page, total=total)


@app.route('/admin/trigger_autodeploy', methods=['POST'])
def trigger_autodeploy():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    if not is_admin_user(user):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    try:
        verify_csrf()
    except Exception:
        flash('Invalid CSRF token', 'error')
        return redirect(url_for('admin_tools'))

    # Enqueue autodeploy task (background)
    try:
        redis_url = os.environ.get('PANEL_REDIS_URL', config.REDIS_URL)
        rconn = redis.from_url(redis_url)
        q = Queue('default', connection=rconn)
        job = q.enqueue(tasks.run_autodeploy, timeout=3600)
        flash(f'Autodeploy enqueued (job id={job.id})', 'info')
        return redirect(url_for('admin_tools'))
    except Exception as e:
        flash(f'Failed to enqueue autodeploy: {e}', 'error')
        return redirect(url_for('admin_tools'))


@app.route('/admin/run_memdump', methods=['POST'])
def run_memdump():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('login'))
    user = db.session.get(User, uid)
    if not is_admin_user(user):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    try:
        verify_csrf()
    except Exception:
        flash('Invalid CSRF token', 'error')
        return redirect(url_for('admin_tools'))

    pid_file = request.form.get('pid_file') or getattr(config, 'ET_PID_FILE', '/var/run/etlegacy.pid')
    # Enqueue memwatch task (background)
    try:
        redis_url = os.environ.get('PANEL_REDIS_URL', config.REDIS_URL)
        rconn = redis.from_url(redis_url)
        q = Queue('default', connection=rconn)
        job = q.enqueue(tasks.run_memwatch, pid_file, timeout=600)
        flash(f'Memwatch enqueued (job id={job.id})', 'info')
        return redirect(url_for('admin_tools'))
    except Exception as e:
        flash(f'Failed to enqueue memwatch: {e}', 'error')
        return redirect(url_for('admin_tools'))


@app.route('/admin/job/<job_id>')
def admin_job_status(job_id):
    try:
        redis_url = os.environ.get('PANEL_REDIS_URL', config.REDIS_URL)
        rconn = redis.from_url(redis_url)
        from rq.job import Job
        job = Job.fetch(job_id, connection=rconn)
        status = job.get_status()
        result = job.result
        return {'id': job_id, 'status': status, 'result': result}
    except Exception as e:
        return {'error': str(e)}, 500


if __name__ == "__main__":
    # create DB tables if not exist
    with app.app_context():
        db.create_all()
        # Simple migration: if theme data exists as files but not in DB, import them
        try:
            # import css file if present and DB empty
            s_css = SiteSetting.query.filter_by(key='custom_theme_css').first()
            theme_path = os.path.join(app.root_path, 'static', 'css', 'custom_theme.css')
            if not s_css and os.path.exists(theme_path):
                with open(theme_path, 'r', encoding='utf-8') as f:
                    css = f.read()
                s_css = SiteSetting(key='custom_theme_css', value=css)
                db.session.add(s_css)

            # import enabled flag from instance file if present and DB empty
            s_flag = SiteSetting.query.filter_by(key='theme_enabled').first()
            flag_path = os.path.join(app.root_path, 'instance', 'theme_enabled')
            if not s_flag and os.path.exists(flag_path):
                try:
                    with open(flag_path, 'r', encoding='utf-8') as f:
                        v = f.read().strip()
                    s_flag = SiteSetting(key='theme_enabled', value=('1' if v == '1' else '0'))
                    db.session.add(s_flag)
                except Exception:
                    pass

            if (s_css or s_flag):
                db.session.commit()
        except Exception:
            db.session.rollback()
    app.run(host="0.0.0.0", port=8080, debug=True)
