"""
Real-Time Server Monitoring and Analytics System

Provides comprehensive server monitoring, performance metrics, and analytics dashboard
for ET:Legacy game servers with live data streaming and alerting capabilities.
"""

import time
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app import db
from sqlalchemy import desc
import subprocess
import psutil
import threading
from collections import defaultdict, deque


monitoring_bp = Blueprint('monitoring', __name__)


class ServerMetrics(db.Model):
    """Store server performance and player metrics."""
    __tablename__ = 'server_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Performance metrics
    cpu_usage = db.Column(db.Float, nullable=True)  # CPU percentage
    memory_usage = db.Column(db.Float, nullable=True)  # Memory in MB
    memory_percentage = db.Column(db.Float, nullable=True)  # Memory percentage
    network_in = db.Column(db.BigInteger, nullable=True)  # Bytes received
    network_out = db.Column(db.BigInteger, nullable=True)  # Bytes sent
    disk_usage = db.Column(db.Float, nullable=True)  # Disk usage percentage
    
    # Server metrics  
    player_count = db.Column(db.Integer, nullable=True)
    max_players = db.Column(db.Integer, nullable=True)
    map_name = db.Column(db.String(128), nullable=True)
    game_mode = db.Column(db.String(64), nullable=True)
    server_fps = db.Column(db.Float, nullable=True)
    tick_rate = db.Column(db.Float, nullable=True)
    
    # Status
    is_online = db.Column(db.Boolean, default=False)
    ping_response_time = db.Column(db.Float, nullable=True)  # Response time in ms
    
    server = db.relationship('Server', backref=db.backref('metrics', lazy='dynamic'))


class PlayerSession(db.Model):
    """Track individual player sessions and activities."""
    __tablename__ = 'player_session'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    player_name = db.Column(db.String(128), nullable=False)
    player_guid = db.Column(db.String(64), nullable=True)
    player_ip = db.Column(db.String(45), nullable=True)  # IPv6 support
    
    session_start = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    session_end = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    
    # Player stats
    kills = db.Column(db.Integer, default=0)
    deaths = db.Column(db.Integer, default=0)
    score = db.Column(db.Integer, default=0)
    team = db.Column(db.String(16), nullable=True)  # axis, allies, spectator
    
    server = db.relationship('Server', backref=db.backref('player_sessions', lazy='dynamic'))


class ServerAlert(db.Model):
    """Server alert definitions and history."""
    __tablename__ = 'server_alert'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=True)  # NULL for global alerts
    alert_type = db.Column(db.String(64), nullable=False)  # cpu_high, memory_high, server_offline, etc.
    threshold_value = db.Column(db.Float, nullable=True)
    comparison_operator = db.Column(db.String(8), nullable=False)  # >, <, ==, !=
    
    is_active = db.Column(db.Boolean, default=True)
    notify_discord = db.Column(db.Boolean, default=False)
    notify_email = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    server = db.relationship('Server', backref=db.backref('alerts', lazy='dynamic'))
    creator = db.relationship('User')


class AlertHistory(db.Model):
    """History of triggered alerts."""
    __tablename__ = 'alert_history'
    
    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey('server_alert.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=True)
    
    triggered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)
    severity = db.Column(db.String(16), default='warning')  # info, warning, critical
    message = db.Column(db.Text, nullable=False)
    
    # Metric values that triggered the alert
    metric_value = db.Column(db.Float, nullable=True)
    threshold_value = db.Column(db.Float, nullable=True)
    
    alert = db.relationship('ServerAlert')
    server = db.relationship('Server')


class ServerMonitor:
    """Real-time server monitoring system."""
    
    def __init__(self):
        self.monitoring_active = False
        self.monitor_thread = None
        self.live_data = defaultdict(lambda: deque(maxlen=60))  # 60 seconds of live data
        
    def start_monitoring(self, app=None):
        """Start the background monitoring thread."""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.app = app
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self):
        """Main monitoring loop - runs every 5 seconds."""
        from app import Server
        
        while self.monitoring_active:
            try:
                if self.app:
                    with self.app.app_context():
                        servers = Server.query.all()
                else:
                    # Fallback without app context (limited functionality)
                    servers = []
                
                for server in servers:
                    metrics = self._collect_server_metrics(server)
                    self._store_metrics(server.id, metrics)
                    self._check_alerts(server, metrics)
                    
                    # Store in live data for real-time dashboard
                    self.live_data[server.id].append({
                        'timestamp': time.time(),
                        'metrics': metrics
                    })
                
                time.sleep(5)  # Monitor every 5 seconds
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(5)
    
    def _collect_server_metrics(self, server):
        """Collect comprehensive metrics for a server."""
        metrics = {
            'timestamp': datetime.now(timezone.utc),
            'cpu_usage': None,
            'memory_usage': None,
            'memory_percentage': None,
            'network_in': None,
            'network_out': None,
            'disk_usage': None,
            'player_count': None,
            'max_players': None,
            'map_name': None,
            'game_mode': None,
            'server_fps': None,
            'is_online': False,
            'ping_response_time': None
        }
        
        try:
            # System metrics (assuming server runs on same host)
            if hasattr(psutil, 'cpu_percent'):
                metrics['cpu_usage'] = psutil.cpu_percent(interval=1)
            
            memory = psutil.virtual_memory()
            metrics['memory_usage'] = memory.used / (1024 * 1024)  # MB
            metrics['memory_percentage'] = memory.percent
            
            disk = psutil.disk_usage('/')
            metrics['disk_usage'] = (disk.used / disk.total) * 100
            
            # Network metrics
            net_io = psutil.net_io_counters()
            metrics['network_in'] = net_io.bytes_recv
            metrics['network_out'] = net_io.bytes_sent
            
        except Exception as e:
            print(f"System metrics error: {e}")
        
        try:
            # Server-specific metrics via RCON
            server_info = self._get_server_info_via_rcon(server)
            if server_info:
                metrics.update(server_info)
                metrics['is_online'] = True
            else:
                # Try ping test as fallback
                metrics['is_online'] = self._ping_server(server)
                
        except Exception as e:
            print(f"Server metrics error: {e}")
            metrics['is_online'] = False
        
        return metrics
    
    def _get_server_info_via_rcon(self, server):
        """Get server information via RCON commands."""
        try:
            from rcon_client import ETLegacyRcon
            
            rcon = ETLegacyRcon()
            
            # Get server status
            status_response = rcon.send('status')
            if not status_response:
                return None
            
            info = {}
            
            # Parse status response for player count, map, etc.
            lines = status_response.split('\n')
            for line in lines:
                if 'map:' in line.lower():
                    info['map_name'] = line.split('map:')[1].strip().split()[0]
                elif 'players:' in line.lower():
                    # Parse "players: 5/32" format
                    parts = line.split('players:')[1].strip().split('/')
                    if len(parts) == 2:
                        info['player_count'] = int(parts[0].strip())
                        info['max_players'] = int(parts[1].strip())
            
            # Get server FPS
            fps_response = rcon.send('developer 1; echo $com_maxfps')
            if fps_response and fps_response.isdigit():
                info['server_fps'] = float(fps_response)
            
            # Get game mode
            gamemode_response = rcon.send('echo $g_gametype')
            if gamemode_response:
                gametype_map = {
                    '2': 'Objective',
                    '3': 'Stopwatch',
                    '4': 'Campaign',
                    '5': 'LMS',
                    '6': 'Map Voting'
                }
                info['game_mode'] = gametype_map.get(gamemode_response.strip(), 'Unknown')
            
            return info
            
        except Exception as e:
            print(f"RCON error for server {server.name}: {e}")
            return None
    
    def _ping_server(self, server):
        """Simple ping test to check if server is responsive."""
        try:
            # Extract host and port from server configuration
            host = getattr(server, 'host', '127.0.0.1')
            port = getattr(server, 'port', 27960)
            
            # Use nc (netcat) to test connection
            result = subprocess.run(
                ['nc', '-z', '-w', '3', host, str(port)],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _store_metrics(self, server_id, metrics):
        """Store metrics in database."""
        try:
            metric_record = ServerMetrics(
                server_id=server_id,
                timestamp=metrics['timestamp'],
                cpu_usage=metrics.get('cpu_usage'),
                memory_usage=metrics.get('memory_usage'),
                memory_percentage=metrics.get('memory_percentage'),
                network_in=metrics.get('network_in'),
                network_out=metrics.get('network_out'),
                disk_usage=metrics.get('disk_usage'),
                player_count=metrics.get('player_count'),
                max_players=metrics.get('max_players'),
                map_name=metrics.get('map_name'),
                game_mode=metrics.get('game_mode'),
                server_fps=metrics.get('server_fps'),
                is_online=metrics.get('is_online', False),
                ping_response_time=metrics.get('ping_response_time')
            )
            
            db.session.add(metric_record)
            db.session.commit()
            
        except Exception as e:
            print(f"Error storing metrics: {e}")
            db.session.rollback()
    
    def _check_alerts(self, server, metrics):
        """Check if any alerts should be triggered."""
        try:
            # Get active alerts for this server and global alerts
            alerts = ServerAlert.query.filter(
                db.or_(
                    ServerAlert.server_id == server.id,
                    ServerAlert.server_id.is_(None)
                ),
                ServerAlert.is_active == True
            ).all()
            
            for alert in alerts:
                should_trigger = False
                metric_value = None
                
                # Check different alert types
                if alert.alert_type == 'cpu_high':
                    metric_value = metrics.get('cpu_usage')
                    if metric_value and self._compare_values(metric_value, alert.comparison_operator, alert.threshold_value):
                        should_trigger = True
                
                elif alert.alert_type == 'memory_high':
                    metric_value = metrics.get('memory_percentage')
                    if metric_value and self._compare_values(metric_value, alert.comparison_operator, alert.threshold_value):
                        should_trigger = True
                
                elif alert.alert_type == 'server_offline':
                    metric_value = 1 if metrics.get('is_online') else 0
                    if self._compare_values(metric_value, alert.comparison_operator, 0):
                        should_trigger = True
                
                elif alert.alert_type == 'player_count_low':
                    metric_value = metrics.get('player_count', 0)
                    if self._compare_values(metric_value, alert.comparison_operator, alert.threshold_value):
                        should_trigger = True
                
                if should_trigger:
                    self._trigger_alert(alert, server, metric_value, metrics)
                    
        except Exception as e:
            print(f"Alert checking error: {e}")
    
    def _compare_values(self, value, operator, threshold):
        """Compare values based on operator."""
        if operator == '>':
            return value > threshold
        elif operator == '<':
            return value < threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return value == threshold
        elif operator == '!=':
            return value != threshold
        return False
    
    def _trigger_alert(self, alert, server, metric_value, metrics):
        """Trigger an alert and send notifications."""
        try:
            # Check if this alert was recently triggered (avoid spam)
            recent_alert = AlertHistory.query.filter(
                AlertHistory.alert_id == alert.id,
                AlertHistory.server_id == server.id,
                AlertHistory.resolved_at.is_(None),
                AlertHistory.triggered_at > datetime.now(timezone.utc) - timedelta(minutes=5)
            ).first()
            
            if recent_alert:
                return  # Don't spam alerts
            
            # Create alert history record
            severity = self._determine_severity(alert.alert_type, metric_value, alert.threshold_value)
            message = self._generate_alert_message(alert, server, metric_value, metrics)
            
            alert_history = AlertHistory(
                alert_id=alert.id,
                server_id=server.id,
                severity=severity,
                message=message,
                metric_value=metric_value,
                threshold_value=alert.threshold_value
            )
            
            db.session.add(alert_history)
            db.session.commit()
            
            # Send notifications
            if alert.notify_discord:
                self._send_discord_notification(alert, server, message, severity)
            
            if alert.notify_email:
                self._send_email_notification(alert, server, message, severity)
                
        except Exception as e:
            print(f"Alert trigger error: {e}")
            db.session.rollback()
    
    def _determine_severity(self, alert_type, value, threshold):
        """Determine alert severity based on how far the value exceeds threshold."""
        if alert_type == 'server_offline':
            return 'critical'
        
        if isinstance(value, (int, float)) and isinstance(threshold, (int, float)):
            if alert_type in ['cpu_high', 'memory_high']:
                if value > threshold * 1.5:
                    return 'critical'
                elif value > threshold * 1.2:
                    return 'warning'
        
        return 'info'
    
    def _generate_alert_message(self, alert, server, metric_value, metrics):
        """Generate human-readable alert message."""
        alert_messages = {
            'cpu_high': f"High CPU usage: {metric_value:.1f}% (threshold: {alert.threshold_value}%)",
            'memory_high': f"High memory usage: {metric_value:.1f}% (threshold: {alert.threshold_value}%)",
            'server_offline': "Server is offline or unresponsive",
            'player_count_low': f"Low player count: {metric_value} players (threshold: {alert.threshold_value})"
        }
        
        base_message = alert_messages.get(alert.alert_type, f"Alert triggered: {alert.alert_type}")
        return f"Server '{server.name}': {base_message}"
    
    def _send_discord_notification(self, alert, server, message, severity):
        """Send Discord webhook notification."""
        try:
            import requests
            import os
            
            webhook_url = os.environ.get('PANEL_DISCORD_WEBHOOK')
            if not webhook_url:
                return
            
            color_map = {
                'info': 0x3498db,      # Blue
                'warning': 0xf39c12,   # Orange  
                'critical': 0xe74c3c   # Red
            }
            
            embed = {
                'title': f'🚨 Server Alert - {severity.title()}',
                'description': message,
                'color': color_map.get(severity, 0x95a5a6),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'fields': [
                    {
                        'name': 'Server',
                        'value': server.name,
                        'inline': True
                    },
                    {
                        'name': 'Alert Type',
                        'value': alert.alert_type.replace('_', ' ').title(),
                        'inline': True
                    }
                ]
            }
            
            payload = {
                'embeds': [embed]
            }
            
            requests.post(webhook_url, json=payload, timeout=10)
            
        except Exception as e:
            print(f"Discord notification error: {e}")
    
    def _send_email_notification(self, alert, server, message, severity):
        """Send email notification (placeholder for email integration)."""
        # This would integrate with your email system
        print(f"EMAIL ALERT: {message}")
    
    def get_live_data(self, server_id):
        """Get recent live monitoring data for a server."""
        return list(self.live_data.get(server_id, []))


# Global monitor instance
server_monitor = ServerMonitor()


@monitoring_bp.route('/admin/monitoring/dashboard')
@login_required
def monitoring_dashboard():
    """Main monitoring dashboard."""
    if not current_user.is_system_admin:
        return redirect(url_for('dashboard'))
    
    from app import Server
    
    servers = Server.query.all()
    
    # Get latest metrics for each server
    server_stats = []
    for server in servers:
        latest_metric = ServerMetrics.query.filter_by(
            server_id=server.id
        ).order_by(desc(ServerMetrics.timestamp)).first()
        
        server_stats.append({
            'server': server,
            'metrics': latest_metric,
            'alert_count': AlertHistory.query.filter(
                AlertHistory.server_id == server.id,
                AlertHistory.resolved_at.is_(None)
            ).count()
        })
    
    return render_template('admin_monitoring_dashboard.html', 
                         server_stats=server_stats)


@monitoring_bp.route('/admin/monitoring/server/<int:server_id>')
@login_required  
def server_monitoring_detail(server_id):
    """Detailed monitoring for a specific server."""
    from app import Server
    
    server = Server.query.get_or_404(server_id)
    
    # Check permissions
    if not (current_user.is_system_admin or server.owner_id == current_user.id):
        return redirect(url_for('dashboard'))
    
    # Get recent metrics (last 24 hours)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    metrics = ServerMetrics.query.filter(
        ServerMetrics.server_id == server_id,
        ServerMetrics.timestamp >= since
    ).order_by(ServerMetrics.timestamp.asc()).all()
    
    # Get recent alerts
    alerts = AlertHistory.query.filter(
        AlertHistory.server_id == server_id
    ).order_by(desc(AlertHistory.triggered_at)).limit(20).all()
    
    # Get recent player sessions
    player_sessions = PlayerSession.query.filter(
        PlayerSession.server_id == server_id
    ).order_by(desc(PlayerSession.session_start)).limit(50).all()
    
    return render_template('admin_monitoring_server_detail.html',
                         server=server,
                         metrics=metrics,
                         alerts=alerts,
                         player_sessions=player_sessions)


@monitoring_bp.route('/api/monitoring/live/<int:server_id>')
@login_required
def live_monitoring_data(server_id):
    """API endpoint for live monitoring data."""
    from app import Server
    
    server = Server.query.get_or_404(server_id)
    
    # Check permissions
    if not (current_user.is_system_admin or server.owner_id == current_user.id):
        return jsonify({'error': 'Access denied'}), 403
    
    live_data = server_monitor.get_live_data(server_id)
    
    return jsonify({
        'success': True,
        'data': live_data,
        'timestamp': time.time()
    })


@monitoring_bp.route('/admin/monitoring/alerts', methods=['GET', 'POST'])
@login_required
def manage_alerts():
    """Manage server alerts."""
    if not current_user.is_system_admin:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            alert = ServerAlert(
                server_id=data.get('server_id'),
                alert_type=data['alert_type'],
                threshold_value=data.get('threshold_value'),
                comparison_operator=data['comparison_operator'],
                notify_discord=data.get('notify_discord', False),
                notify_email=data.get('notify_email', False),
                created_by=current_user.id
            )
            
            db.session.add(alert)
            db.session.commit()
            
            return jsonify({'success': True, 'alert_id': alert.id})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET - show alerts management page
    alerts = ServerAlert.query.order_by(desc(ServerAlert.created_at)).all()
    return render_template('admin_monitoring_alerts.html', alerts=alerts)


def start_monitoring(app=None):
    """Start the monitoring system."""
    try:
        server_monitor.start_monitoring(app)
    except Exception as e:
        print(f"Error starting monitoring: {e}")


def stop_monitoring():
    """Stop the monitoring system."""
    server_monitor.stop_monitoring()