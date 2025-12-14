"""Simple mail tool used in tests."""
import smtplib
from email.message import EmailMessage

class Mail:
    def init_app(self, app):
        # No-op initializer for tests
        return True
    def send_message(self, subject: str, body: str, to: str, sender: str = "noreply@example.com") -> bool:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to
        msg.set_content(body)
        # In tests, smtplib.SMTP will be monkeypatched
        smtp = smtplib.SMTP("localhost", 25)
        try:
            smtp.send_message(msg)
        finally:
            try:
                smtp.quit()
            except Exception:
                pass
        return True

mail = Mail()
