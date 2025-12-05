# app/modules/mobile_app/mobile_manager.py

"""
Mobile Application & Remote Management for Panel Application
Native mobile app for server management
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import time


@dataclass
class MobileAlert:
    """Mobile push notification alert"""
    alert_id: str
    title: str
    message: str
    severity: str
    timestamp: float


@dataclass
class ServerCommand:
    """Remote server command"""
    command_id: str
    server_id: str
    command: str
    parameters: Dict[str, Any]
    status: str
    timestamp: float


class MobileApplicationManager:
    """
    Mobile app integration for remote server management
    """

    def __init__(self):
        self.connected_devices: Dict[str, Dict] = {}
        self.pending_alerts: List[MobileAlert] = []
        self.command_queue: List[ServerCommand] = []

    def register_device(self, device_token: str, user_id: str) -> bool:
        """Register mobile device for push notifications"""
        self.connected_devices[device_token] = {
            "user_id": user_id,
            "registered_at": time.time(),
            "last_active": time.time()
        }
        return True

    def send_push_notification(self, user_id: str, title: str, message: str, severity: str = "info"):
        """Send push notification to user's devices"""
        alert = MobileAlert(
            alert_id=f"alert_{int(time.time())}",
            title=title,
            message=message,
            severity=severity,
            timestamp=time.time()
        )

        # Find user's devices
        user_devices = [token for token, data in self.connected_devices.items()
                       if data["user_id"] == user_id]

        for device_token in user_devices:
            self._send_to_device(device_token, alert)

        self.pending_alerts.append(alert)

    def queue_server_command(self, server_id: str, command: str, parameters: Dict = None) -> str:
        """Queue command for remote server execution"""
        cmd = ServerCommand(
            command_id=f"cmd_{int(time.time())}",
            server_id=server_id,
            command=command,
            parameters=parameters or {},
            status="queued",
            timestamp=time.time()
        )

        self.command_queue.append(cmd)
        return cmd.command_id

    def get_pending_commands(self, server_id: str) -> List[ServerCommand]:
        """Get pending commands for server"""
        return [cmd for cmd in self.command_queue
                if cmd.server_id == server_id and cmd.status == "queued"]

    def _send_to_device(self, device_token: str, alert: MobileAlert):
        """Send notification to specific device"""
        # In production, integrate with FCM/APNs
        print(f"Sending notification to {device_token}: {alert.title}")


# Global mobile app manager
mobile_app_manager = MobileApplicationManager()