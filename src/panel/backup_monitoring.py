"""
Backup Monitoring and Alerting
Monitor backup health and send alerts for issues
"""

import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import json
from pathlib import Path

from src.panel.backup_recovery import get_backup_manager


class BackupMonitor:
    """Monitor backup system health and performance"""

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.alerts_sent: Dict[str, datetime] = {}
        self.monitoring_config = {
            'max_backup_age_hours': 25,  # Alert if no backup in 25 hours
            'min_backup_success_rate': 0.95,  # Alert if success rate < 95%
            'max_backup_duration_minutes': 120,  # Alert if backup takes > 2 hours
            'alert_cooldown_hours': 6,  # Don't send same alert more than once every 6 hours
            'email_enabled': app.config.get('BACKUP_EMAIL_ALERTS', True),
            'email_recipients': app.config.get('BACKUP_ALERT_EMAILS', '').split(','),
            'email_sender': app.config.get('BACKUP_EMAIL_SENDER', 'noreply@panel.local'),
            'smtp_server': app.config.get('SMTP_SERVER', 'localhost'),
            'smtp_port': app.config.get('SMTP_PORT', 587),
            'smtp_username': app.config.get('SMTP_USERNAME'),
            'smtp_password': app.config.get('SMTP_PASSWORD')
        }

    def check_backup_health(self) -> Dict[str, Any]:
        """Check overall backup system health"""
        manager = get_backup_manager()
        backups = manager.list_backups()

        if not backups:
            return {
                'status': 'error',
                'message': 'No backups found',
                'issues': ['No backup history available']
            }

        # Analyze backup health
        health_report = {
            'status': 'healthy',
            'total_backups': len(backups),
            'last_backup_time': None,
            'backup_success_rate': 0.0,
            'average_backup_size': 0,
            'issues': [],
            'recommendations': []
        }

        # Calculate metrics
        completed_backups = [b for b in backups if b['status'] == 'completed']
        failed_backups = [b for b in backups if b['status'] == 'failed']

        if completed_backups:
            health_report['backup_success_rate'] = len(completed_backups) / len(backups)
            health_report['average_backup_size'] = sum(b['size_bytes'] for b in completed_backups) / len(completed_backups)

            # Find latest backup
            latest_backup = max(completed_backups, key=lambda x: x['created_at'])
            health_report['last_backup_time'] = latest_backup['created_at']

        # Check for issues
        issues = []

        # Check backup age
        if health_report['last_backup_time']:
            last_backup_dt = datetime.fromisoformat(health_report['last_backup_time'].replace('Z', '+00:00'))
            hours_since_last_backup = (datetime.utcnow() - last_backup_dt).total_seconds() / 3600

            if hours_since_last_backup > self.monitoring_config['max_backup_age_hours']:
                issues.append(f'No successful backup in {hours_since_last_backup:.1f} hours')

        # Check success rate
        if health_report['backup_success_rate'] < self.monitoring_config['min_backup_success_rate']:
            success_percent = health_report['backup_success_rate'] * 100
            issues.append(f'Backup success rate is only {success_percent:.1f}%')

        # Check for recent failures
        recent_failures = []
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        for backup in failed_backups:
            backup_time = datetime.fromisoformat(backup['created_at'].replace('Z', '+00:00'))
            if backup_time > one_day_ago:
                recent_failures.append(backup)

        if recent_failures:
            issues.append(f'{len(recent_failures)} backup(s) failed in the last 24 hours')

        # Check backup types coverage
        backup_types = set(b['type'] for b in completed_backups)
        required_types = {'database', 'filesystem', 'configuration'}
        missing_types = required_types - backup_types

        if missing_types:
            issues.append(f'Missing backups for types: {", ".join(missing_types)}')

        # Generate recommendations
        recommendations = []

        if not issues:
            recommendations.append('All backup systems are healthy')
        else:
            if 'database' in missing_types:
                recommendations.append('Schedule regular database backups')
            if 'filesystem' in missing_types:
                recommendations.append('Configure filesystem backup automation')
            if health_report['backup_success_rate'] < 0.95:
                recommendations.append('Investigate and fix backup failures')
            if hours_since_last_backup > 24:
                recommendations.append('Review backup scheduling configuration')

        health_report['issues'] = issues
        health_report['recommendations'] = recommendations

        # Set overall status
        if issues:
            health_report['status'] = 'warning' if len(issues) < 3 else 'error'

        return health_report

    def check_storage_health(self) -> Dict[str, Any]:
        """Check backup storage health"""
        manager = get_backup_manager()
        backup_dir = Path(manager.config.storage_path)

        storage_report = {
            'status': 'healthy',
            'total_size_bytes': 0,
            'file_count': 0,
            'oldest_backup_days': 0,
            'newest_backup_days': 0,
            'issues': [],
            'disk_usage_percent': 0
        }

        if not backup_dir.exists():
            return {
                'status': 'error',
                'issues': ['Backup directory does not exist']
            }

        # Analyze backup files
        backup_files = list(backup_dir.glob('*'))
        backup_files = [f for f in backup_files if f.is_file()]

        if not backup_files:
            return {
                'status': 'warning',
                'issues': ['No backup files found in storage directory']
            }

        storage_report['file_count'] = len(backup_files)

        # Calculate total size
        total_size = sum(f.stat().st_size for f in backup_files)
        storage_report['total_size_bytes'] = total_size

        # Get file timestamps
        file_times = [f.stat().st_mtime for f in backup_files]
        oldest_time = min(file_times)
        newest_time = max(file_times)

        now = time.time()
        storage_report['oldest_backup_days'] = (now - oldest_time) / (24 * 3600)
        storage_report['newest_backup_days'] = (now - newest_time) / (24 * 3600)

        # Check disk usage
        try:
            stat = os.statvfs(backup_dir)
            disk_usage_percent = ((stat.f_blocks - stat.f_bavail) / stat.f_blocks) * 100
            storage_report['disk_usage_percent'] = disk_usage_percent

            if disk_usage_percent > 90:
                storage_report['issues'].append(f'Disk usage is {disk_usage_percent:.1f}% - consider cleanup')
                storage_report['status'] = 'warning'
            elif disk_usage_percent > 95:
                storage_report['issues'].append(f'Critical disk usage: {disk_usage_percent:.1f}%')
                storage_report['status'] = 'error'
        except OSError:
            storage_report['issues'].append('Unable to check disk usage')

        # Check for very old backups
        if storage_report['oldest_backup_days'] > 90:
            storage_report['issues'].append('Some backups are older than 90 days')
            storage_report['status'] = 'warning'

        return storage_report

    def send_alert(self, alert_type: str, subject: str, message: str):
        """Send an alert notification"""
        # Check cooldown
        now = datetime.utcnow()
        last_sent = self.alerts_sent.get(alert_type)

        if last_sent and (now - last_sent).total_seconds() < (self.monitoring_config['alert_cooldown_hours'] * 3600):
            self.logger.info(f"Alert '{alert_type}' skipped due to cooldown")
            return

        self.alerts_sent[alert_type] = now

        # Send email alert
        if self.monitoring_config['email_enabled']:
            self._send_email_alert(subject, message)

        # Log alert
        self.logger.warning(f"Backup Alert: {subject} - {message}")

    def _send_email_alert(self, subject: str, message: str):
        """Send email alert"""
        if not self.monitoring_config['email_recipients']:
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.monitoring_config['email_sender']
            msg['To'] = ', '.join(self.monitoring_config['email_recipients'])
            msg['Subject'] = f"[Panel Backup Alert] {subject}"

            msg.attach(MIMEText(message, 'plain'))

            server = smtplib.SMTP(
                self.monitoring_config['smtp_server'],
                self.monitoring_config['smtp_port']
            )

            if self.monitoring_config['smtp_username']:
                server.starttls()
                server.login(
                    self.monitoring_config['smtp_username'],
                    self.monitoring_config['smtp_password']
                )

            server.send_message(msg)
            server.quit()

            self.logger.info(f"Backup alert email sent to {len(self.monitoring_config['email_recipients'])} recipients")

        except Exception as e:
            self.logger.error(f"Failed to send backup alert email: {e}")

    def generate_health_report(self) -> str:
        """Generate comprehensive health report"""
        backup_health = self.check_backup_health()
        storage_health = self.check_storage_health()

        report_lines = []
        report_lines.append("# Backup System Health Report")
        report_lines.append(f"Generated: {datetime.utcnow().isoformat()}")
        report_lines.append("")

        # Overall status
        overall_status = 'healthy'
        if backup_health['status'] == 'error' or storage_health['status'] == 'error':
            overall_status = 'error'
        elif backup_health['status'] == 'warning' or storage_health['status'] == 'warning':
            overall_status = 'warning'

        status_icon = {'healthy': '?', 'warning': '??', 'error': '?'}[overall_status]
        report_lines.append(f"## Overall Status: {status_icon} {overall_status.upper()}")
        report_lines.append("")

        # Backup health
        report_lines.append("## Backup Health")
        report_lines.append(f"- Total backups: {backup_health['total_backups']}")
        report_lines.append(f"- Success rate: {backup_health['backup_success_rate']*100:.1f}%")

        if backup_health['last_backup_time']:
            report_lines.append(f"- Last backup: {backup_health['last_backup_time']}")
            last_backup_dt = datetime.fromisoformat(backup_health['last_backup_time'].replace('Z', '+00:00'))
            hours_ago = (datetime.utcnow() - last_backup_dt).total_seconds() / 3600
            report_lines.append(f"- Hours since last backup: {hours_ago:.1f}")

        if backup_health['average_backup_size']:
            size_mb = backup_health['average_backup_size'] / (1024 * 1024)
            report_lines.append(f"- Average backup size: {size_mb:.2f} MB")

        report_lines.append("")

        # Storage health
        report_lines.append("## Storage Health")
        report_lines.append(f"- Backup files: {storage_health['file_count']}")

        if storage_health['total_size_bytes']:
            size_gb = storage_health['total_size_bytes'] / (1024 * 1024 * 1024)
            report_lines.append(f"- Total size: {size_gb:.2f} GB")

        report_lines.append(f"- Oldest backup: {storage_health['oldest_backup_days']:.1f} days ago")
        report_lines.append(f"- Newest backup: {storage_health['newest_backup_days']:.1f} days ago")
        report_lines.append(f"- Disk usage: {storage_health['disk_usage_percent']:.1f}%")

        report_lines.append("")

        # Issues
        all_issues = backup_health['issues'] + storage_health['issues']
        if all_issues:
            report_lines.append("## Issues Found")
            for issue in all_issues:
                report_lines.append(f"- {issue}")
            report_lines.append("")

        # Recommendations
        all_recommendations = backup_health['recommendations']
        if all_recommendations:
            report_lines.append("## Recommendations")
            for rec in all_recommendations:
                report_lines.append(f"- {rec}")
            report_lines.append("")

        return "\n".join(report_lines)

    def run_monitoring_checks(self):
        """Run all monitoring checks and send alerts if needed"""
        self.logger.info("Running backup monitoring checks...")

        # Check backup health
        backup_health = self.check_backup_health()
        if backup_health['status'] != 'healthy':
            severity = "CRITICAL" if backup_health['status'] == 'error' else "WARNING"
            issues_text = "; ".join(backup_health['issues'])
            self.send_alert(
                'backup_health',
                f"{severity}: Backup System Issues",
                f"Backup system health: {backup_health['status'].upper()}\nIssues: {issues_text}"
            )

        # Check storage health
        storage_health = self.check_storage_health()
        if storage_health['status'] != 'healthy':
            severity = "CRITICAL" if storage_health['status'] == 'error' else "WARNING"
            issues_text = "; ".join(storage_health['issues'])
            self.send_alert(
                'storage_health',
                f"{severity}: Backup Storage Issues",
                f"Storage health: {storage_health['status'].upper()}\nIssues: {issues_text}"
            )

        self.logger.info("Backup monitoring checks completed")


# Global monitor instance
backup_monitor = None

def init_backup_monitoring(app):
    """Initialize backup monitoring"""
    global backup_monitor
    backup_monitor = BackupMonitor(app)
    return backup_monitor


def get_backup_monitor() -> BackupMonitor:
    """Get the global backup monitor"""
    return backup_monitor


# Utility functions for external monitoring
def check_backup_health() -> Dict[str, Any]:
    """Check backup system health (for external monitoring)"""
    monitor = get_backup_monitor()
    return monitor.check_backup_health()


def check_storage_health() -> Dict[str, Any]:
    """Check backup storage health (for external monitoring)"""
    monitor = get_backup_monitor()
    return monitor.check_storage_health()


def generate_health_report() -> str:
    """Generate backup health report"""
    monitor = get_backup_monitor()
    return monitor.generate_health_report()


def run_monitoring_checks():
    """Run monitoring checks (for cron jobs)"""
    monitor = get_backup_monitor()
    monitor.run_monitoring_checks()