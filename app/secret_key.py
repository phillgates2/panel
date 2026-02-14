import os
import secrets
from pathlib import Path
from typing import Iterable, Optional

from flask import Flask


def ensure_secret_key(
    app: Flask,
    *,
    candidates: Optional[Iterable[Optional[str]]] = None,
    persist: bool = True,
    filename: str = "secret_key",
) -> str:
    """Ensure the Flask app has a usable secret key.

    Priority order:
    - existing app.secret_key / app.config['SECRET_KEY']
    - provided candidates
    - env vars PANEL_SECRET_KEY / SECRET_KEY
    - persisted instance file (default: instance/secret_key)
    - generated random secret (persisted when possible)
    """

    secret_key = app.secret_key or app.config.get("SECRET_KEY")

    if not secret_key and candidates:
        for candidate in candidates:
            if candidate:
                secret_key = candidate
                break

    if not secret_key:
        secret_key = os.environ.get("PANEL_SECRET_KEY") or os.environ.get("SECRET_KEY")

    secret_path = None
    if persist:
        try:
            Path(app.instance_path).mkdir(parents=True, exist_ok=True)
            secret_path = Path(app.instance_path) / filename
            if not secret_key and secret_path.exists():
                secret_key = secret_path.read_text(encoding="utf-8").strip() or None
        except Exception:
            secret_path = None

    if not secret_key:
        secret_key = secrets.token_urlsafe(48)
        if persist and secret_path is not None:
            try:
                secret_path.write_text(secret_key, encoding="utf-8")
                os.chmod(secret_path, 0o600)
            except Exception:
                pass

    app.config["SECRET_KEY"] = secret_key
    app.secret_key = secret_key
    return secret_key
