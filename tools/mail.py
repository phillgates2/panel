"""Lightweight SMTP mail client wrapper.

This small utility avoids adding external dependencies and provides a
simple `Mail` class that can be used from within views or tasks.

Configuration (read from `app.config`):
- MAIL_SERVER: hostname (default 'localhost')
- MAIL_PORT: port (default 25)
- MAIL_USE_TLS: bool
- MAIL_USE_SSL: bool
- MAIL_USERNAME / MAIL_PASSWORD: optional for auth
- MAIL_DEFAULT_SENDER: default from address
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Optional


class Mail:
    def __init__(self, app=None):
        self.app = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

    def _get_connection(self):
        if self.app is None:
            raise RuntimeError("Mail not initialized")
        host = self.app.config.get("MAIL_SERVER", "localhost")
        port = int(self.app.config.get("MAIL_PORT", 25))
        use_tls = bool(self.app.config.get("MAIL_USE_TLS", False))
        use_ssl = bool(self.app.config.get("MAIL_USE_SSL", False))
        username = self.app.config.get("MAIL_USERNAME")
        password = self.app.config.get("MAIL_PASSWORD")

        if use_ssl:
            conn = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            conn = smtplib.SMTP(host, port, timeout=30)
        conn.ehlo()
        if use_tls and not use_ssl:
            conn.starttls()
            conn.ehlo()
        if username and password:
            conn.login(username, password)
        return conn

    def send_message(
        self,
        subject: str,
        body: str,
        recipients,
        sender: Optional[str] = None,
        html: Optional[str] = None,
    ):
        """Send an email. `recipients` can be a string or a list/tuple."""
        if self.app is None:
            raise RuntimeError("Mail not initialized")
        if isinstance(recipients, str):
            recipients = [recipients]
        sender = sender or self.app.config.get("MAIL_DEFAULT_SENDER")
        msg = EmailMessage()
        msg["Subject"] = subject
        if sender:
            msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)
        if html:
            msg.add_alternative(html, subtype="html")

        conn = None
        try:
            conn = self._get_connection()
            conn.send_message(msg)
        finally:
            if conn:
                try:
                    conn.quit()
                except Exception:
                    pass


mail = Mail()
