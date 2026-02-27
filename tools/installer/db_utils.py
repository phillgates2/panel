from __future__ import annotations

from urllib.parse import quote_plus, urlencode, urlparse


_SSL_MODES = {
    "disable",
    "allow",
    "prefer",
    "require",
    "verify-ca",
    "verify-full",
}


def is_postgres_uri(db_uri: str | None) -> bool:
    uri = (db_uri or "").strip()
    if not uri:
        return False
    scheme = (urlparse(uri).scheme or "").lower()
    return scheme.startswith("postgres")


def validate_postgres_ssl_options(
    *,
    sslmode: str | None,
    sslrootcert: str | None,
    sslcert: str | None,
    sslkey: str | None,
) -> str | None:
    mode = (sslmode or "").strip().lower() or None
    if not mode:
        return None
    if mode not in _SSL_MODES:
        return f"Unsupported sslmode: {sslmode!r}"

    # When verifying the server cert, libpq requires a CA file.
    if mode in {"verify-ca", "verify-full"} and not (sslrootcert or "").strip():
        return f"sslmode={mode!r} requires sslrootcert"

    # If a client cert is specified, require a client key too (and vice versa).
    if (sslcert or "").strip() and not (sslkey or "").strip():
        return "sslcert requires sslkey"
    if (sslkey or "").strip() and not (sslcert or "").strip():
        return "sslkey requires sslcert"

    return None


def build_postgres_uri(
    *,
    host: str,
    port: int,
    db_name: str,
    user: str,
    password: str,
    sslmode: str | None = None,
    sslrootcert: str | None = None,
    sslcert: str | None = None,
    sslkey: str | None = None,
) -> str:
    """Build a PostgreSQL SQLAlchemy URL.

    Uses the `postgresql+psycopg2://` dialect/driver to match the rest of the
    installer code.
    """
    q: dict[str, str] = {}
    mode = (sslmode or "").strip().lower()
    if mode:
        q["sslmode"] = mode
    if (sslrootcert or "").strip():
        q["sslrootcert"] = (sslrootcert or "").strip()
    if (sslcert or "").strip():
        q["sslcert"] = (sslcert or "").strip()
    if (sslkey or "").strip():
        q["sslkey"] = (sslkey or "").strip()

    qs = ("?" + urlencode(q)) if q else ""

    # Keep host as-is (may be hostname or IP); quote user/pass.
    return (
        "postgresql+psycopg2://"
        f"{quote_plus(user)}:{quote_plus(password)}@{host}:{int(port)}/{db_name}"
        f"{qs}"
    )
