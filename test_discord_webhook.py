#!/usr/bin/env python3
"""
Discord Webhook Test Script

Test the enhanced Discord webhook functionality with server player statistics.
"""

import os
import sys
from datetime import datetime, timezone
import pytest

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_discord_webhook():
    """Test the Discord webhook with server stats."""
    try:
        # Import the webhook function
        from src.panel.tasks import _discord_post, _get_server_player_stats

        print("?? Testing Discord webhook with server player statistics...")

        # Test basic webhook
        test_payload = {
            "embeds": [{
                "title": "?? Discord Webhook Test",
                "description": "Testing enhanced webhook with server player statistics",
                "color": 0x3498DB,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "fields": [
                    {
                        "name": "?? Test Type",
                        "value": "Server Statistics Integration",
                        "inline": True
                    }
                ]
            }]
        }

        print("?? Sending test webhook...")
        _discord_post(test_payload)

        # Test server stats function
        print("?? Getting server statistics...")
        stats = _get_server_player_stats()
        if stats:
            print(f"? Found {len(stats)} server stat fields")
            for stat in stats[:3]:  # Show first 3
                print(f"   - {stat['name']}: {stat['value']}")
        else:
            print("??  No server statistics available (this is normal if no servers exist)")

        # Test server status task
        print("?? Testing server status task...")
        from src.panel.tasks import send_server_status_task

        result = send_server_status_task()
        print(f"?? Task result: {result}")

        print("? Discord webhook test completed successfully!")
        assert True

    except Exception as e:
        import traceback
        traceback.print_exc()
        pytest.fail(f"Discord webhook test failed: {e}")


def show_webhook_config():
    """Show current webhook configuration."""
    print("\n?? Discord Webhook Configuration:")
    print("=" * 50)

    webhook_url = os.environ.get("PANEL_DISCORD_WEBHOOK", "")
    if webhook_url:
        # Mask the URL for security
        masked_url = webhook_url[:50] + "..." + webhook_url[-10:] if len(webhook_url) > 60 else webhook_url
        print(f"? Webhook URL: {masked_url}")
    else:
        print("? No webhook URL configured")
        print("   Set PANEL_DISCORD_WEBHOOK environment variable")

    # Check for alternative config
    try:
        from src.panel import config
        alt_webhook = getattr(config, "DISCORD_WEBHOOK", "")
        if alt_webhook and alt_webhook != webhook_url:
            print(f"??  Alternative webhook found in config: {alt_webhook[:50]}...")
    except ImportError:
        print("??  Config module not available")

if __name__ == "__main__":
    print("?? Panel Discord Webhook Test")
    print("=" * 40)

    show_webhook_config()

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Run test and exit with appropriate code
        try:
            test_discord_webhook()
            sys.exit(0)
        except SystemExit:
            raise
        except Exception:
            sys.exit(1)
    else:
        print("\n?? Usage:")
        print("  python test_discord_webhook.py --test    # Run the test")
        print("  python test_discord_webhook.py           # Show configuration only")