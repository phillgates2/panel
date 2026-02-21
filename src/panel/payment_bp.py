import os

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from src.panel.models import Donation, db

payment_bp = Blueprint("payment", __name__)


@payment_bp.route("/donate")
def donate():
    return render_template("donate.html")


@payment_bp.route("/create-payment-intent", methods=["POST"])
def create_payment_intent():
    import stripe

    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_...")

    data = request.json
    amount = data.get("amount", 500)  # cents
    email = data.get("email")

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="usd",
            automatic_payment_methods={"enabled": True},
            receipt_email=email if email else None,
        )
        return {"clientSecret": intent.client_secret}
    except Exception as e:
        return {"error": str(e)}, 400


@payment_bp.route("/webhooks/stripe", methods=["POST"])
def stripe_webhook():
    import stripe

    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400

    # Handle the event
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        # Save donation
        save_donation(payment_intent)
        # Send confirmation email
        send_donation_email(payment_intent)
        print(f"Payment succeeded: {payment_intent['id']}")
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        # Save failed donation
        save_donation(payment_intent, status="failed")
        print(f"Payment failed: {payment_intent['id']}")

    return "", 200


def save_donation(payment_intent, status="completed"):
    """Save donation to database"""
    donation = Donation(
        stripe_payment_id=payment_intent["id"],
        amount=payment_intent["amount"],
        currency=payment_intent.get("currency", "usd"),
        donor_email=payment_intent.get("receipt_email"),
        status=status,
    )
    db.session.add(donation)
    db.session.commit()


def send_donation_email(payment_intent):
    """Send donation confirmation email"""
    try:
        from flask_mail import Message

        from src.panel import mail

        donor_email = payment_intent.get("receipt_email")
        if not donor_email:
            return

        amount = payment_intent["amount"] / 100  # Convert cents to dollars

        msg = Message(
            subject="Thank you for your donation!",
            recipients=[donor_email],
            body=f"Thank you for your generous donation of ${amount:.2f} to Panel. Your support helps us maintain and improve the platform.",
        )
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send donation email: {e}")


@payment_bp.route("/admin/donation-analytics")
def donation_analytics():
    is_admin = callable(getattr(current_user, "is_system_admin", None)) and current_user.is_system_admin()
    if not getattr(current_user, "is_authenticated", False) or not is_admin:
        return redirect(url_for("main.login"))
    return render_template("admin_donation_analytics.html")


@payment_bp.route("/api/donation-analytics")
def donation_analytics_data():
    is_admin = callable(getattr(current_user, "is_system_admin", None)) and current_user.is_system_admin()
    if not getattr(current_user, "is_authenticated", False) or not is_admin:
        return {"error": "Unauthorized"}, 403

    from sqlalchemy import func

    # Total donations
    total = db.session.query(func.sum(Donation.amount)).scalar() or 0
    total /= 100  # Convert to dollars

    monthly = (
        db.session.query(
            func.date_trunc("month", Donation.timestamp).label("month"),
            func.sum(Donation.amount).label("amount"),
        )
        .filter(Donation.status == "completed")
        .group_by("month")
        .order_by("month")
        .all()
    )
    monthly_data = [
        {"month": str(m.month)[:7], "amount": (m.amount or 0) / 100} for m in monthly
    ]

    return {"total": total, "monthly": monthly_data, "count": len(monthly_data)}
