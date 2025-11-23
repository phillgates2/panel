"""
Push Notification Service for PWA
Handles web push notifications using VAPID
"""

import json
import time
from typing import Dict, List, Any, Optional

from pywebpush import webpush, WebPushException

from src.panel import db
from src.panel.models import User, NotificationSubscription


class PushNotificationService:
    """Service for managing push notifications"""

    def __init__(self, vapid_private_key: str, vapid_public_key: str, vapid_subject: str):
        self.vapid_private_key = vapid_private_key
        self.vapid_public_key = vapid_public_key
        self.vapid_subject = vapid_subject

    def subscribe_user(self, user_id: int, subscription_data: Dict[str, Any]) -> bool:
        """Subscribe a user to push notifications"""
        try:
            # Check if subscription already exists
            existing = NotificationSubscription.query.filter_by(
                user_id=user_id,
                endpoint=subscription_data['endpoint']
            ).first()

            if existing:
                # Update existing subscription
                existing.subscription_data = json.dumps(subscription_data)
                existing.last_updated = db.func.now()
            else:
                # Create new subscription
                subscription = NotificationSubscription(
                    user_id=user_id,
                    endpoint=subscription_data['endpoint'],
                    subscription_data=json.dumps(subscription_data)
                )
                db.session.add(subscription)

            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Failed to subscribe user {user_id}: {e}")
            return False

    def unsubscribe_user(self, user_id: int, endpoint: str) -> bool:
        """Unsubscribe a user from push notifications"""
        try:
            NotificationSubscription.query.filter_by(
                user_id=user_id,
                endpoint=endpoint
            ).delete()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Failed to unsubscribe user {user_id}: {e}")
            return False

    def send_notification(self, user_id: int, title: str, body: str,
                         url: str = "/", icon: str = None, badge: str = None) -> bool:
        """Send push notification to a specific user"""
        subscriptions = NotificationSubscription.query.filter_by(user_id=user_id).all()

        if not subscriptions:
            return False

        success_count = 0
        for subscription in subscriptions:
            try:
                subscription_data = json.loads(subscription.subscription_data)

                payload = {
                    "title": title,
                    "body": body,
                    "url": url,
                    "icon": icon or "/static/icons/icon-192.png",
                    "badge": badge or "/static/icons/icon-192.png",
                    "timestamp": int(time.time() * 1000)
                }

                webpush(
                    subscription_info=subscription_data,
                    data=json.dumps(payload),
                    vapid_private_key=self.vapid_private_key,
                    vapid_claims={
                        "sub": self.vapid_subject
                    }
                )

                success_count += 1

            except WebPushException as e:
                print(f"WebPush error for user {user_id}: {e}")
                # Remove invalid subscriptions
                if e.response.status_code in [400, 404, 410]:
                    db.session.delete(subscription)

            except Exception as e:
                print(f"Failed to send notification to user {user_id}: {e}")

        db.session.commit()
        return success_count > 0

    def send_broadcast(self, user_ids: List[int], title: str, body: str,
                      url: str = "/", icon: str = None) -> int:
        """Send push notification to multiple users"""
        success_count = 0
        for user_id in user_ids:
            if self.send_notification(user_id, title, body, url, icon):
                success_count += 1
        return success_count

    def get_user_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all subscriptions for a user"""
        subscriptions = NotificationSubscription.query.filter_by(user_id=user_id).all()
        return [{
            'id': sub.id,
            'endpoint': sub.endpoint,
            'user_agent': sub.user_agent,
            'last_updated': sub.last_updated.isoformat() if sub.last_updated else None
        } for sub in subscriptions]

    def cleanup_expired_subscriptions(self) -> int:
        """Remove subscriptions that are no longer valid"""
        # This would typically involve checking with push services
        # For now, just remove very old subscriptions
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        deleted_count = NotificationSubscription.query.filter(
            NotificationSubscription.created_at < cutoff_date
        ).delete()
        db.session.commit()
        return deleted_count


# Global instance
push_service = None

def init_push_notifications(app) -> None:
    """Initialize push notification service"""
    global push_service

    vapid_private = app.config.get('VAPID_PRIVATE_KEY')
    vapid_public = app.config.get('VAPID_PUBLIC_KEY')
    vapid_subject = app.config.get('VAPID_SUBJECT', 'mailto:admin@panel.local')

    if vapid_private and vapid_public:
        push_service = PushNotificationService(vapid_private, vapid_public, vapid_subject)
        app.logger.info("Push notification service initialized")
    else:
        app.logger.warning("Push notifications disabled - VAPID keys not configured")

def get_push_service() -> Optional[PushNotificationService]:
    """Get the global push service instance"""
    return push_service