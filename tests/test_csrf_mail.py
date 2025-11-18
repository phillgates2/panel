import smtplib
from app import db
from datetime import datetime


def test_csrf_enforced_when_testing_disabled(client, app):
    # Create a thread to reply to
    with app.app_context():
        from forum import Thread
        t = Thread(title='CSRF Test Thread')
        db.session.add(t)
        db.session.commit()
        tid = t.id

    # ensure CSRF checking is active
    app.config['TESTING'] = False

    # Post without csrf_token should fail with 400
    rv = client.post(f'/forum/thread/{tid}/reply', data={'author': 'X', 'content': 'No token'})
    assert rv.status_code == 400


class DummySMTP:
    def __init__(self, *a, **k):
        self.sent = []
        self.closed = False

    def ehlo(self):
        return

    def starttls(self):
        return

    def login(self, u, p):
        self._login = (u, p)

    def send_message(self, msg):
        self.sent.append(msg)

    def quit(self):
        self.closed = True


def test_mail_send_uses_smtp(monkeypatch, app):
    # Ensure mail is initialized
    from tools.mail import mail

    # Configure app mail settings
    app.config['MAIL_SERVER'] = 'localhost'
    app.config['MAIL_PORT'] = 25
    app.config['MAIL_DEFAULT_SENDER'] = 'noreply@example.com'

    mail.init_app(app)

    dummy = DummySMTP()

    def fake_smtp(*a, **k):
        return dummy

    monkeypatch.setattr(smtplib, 'SMTP', fake_smtp)
    monkeypatch.setattr(smtplib, 'SMTP_SSL', fake_smtp)

    # send message
    mail.send_message('Hi', 'Body', ['u@example.com'])

    assert len(dummy.sent) == 1
    msg = dummy.sent[0]
    assert msg['Subject'] == 'Hi'
    assert 'u@example.com' in msg['To']
*** End Patch