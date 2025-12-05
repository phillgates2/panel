# app/modules/ui_dashboard/dashboard.py

"""
Advanced User Interface & Web Dashboard for Panel Application
Modern React-based admin dashboard with real-time monitoring
"""

import asyncio
import json
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import websockets
import flask
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""
    widget_id: str
    widget_type: str
    title: str
    position: Dict[str, int]
    size: Dict[str, int]
    config: Dict[str, Any]
    data_source: str


@dataclass
class DashboardAlert:
    """Dashboard alert configuration"""
    alert_id: str
    condition: str
    threshold: float
    severity: str
    message: str
    active: bool


class PanelDashboard:
    """
    Modern web dashboard for Panel server management
    """

    def __init__(self, host: str = '0.0.0.0', port: int = 5001):
        self.host = host
        self.port = port
        self.app = Flask(__name__,
                        template_folder='templates',
                        static_folder='static')
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        # Dashboard state
        self.widgets: Dict[str, DashboardWidget] = {}
        self.alerts: Dict[str, DashboardAlert] = {}
        self.connected_clients: set = set()
        self.realtime_data: Dict[str, Any] = {}

        # Initialize dashboard
        self._setup_routes()
        self._setup_socket_events()
        self._start_background_tasks()

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def dashboard():
            return render_template('dashboard.html')

        @self.app.route('/api/dashboard/widgets')
        def get_widgets():
            return jsonify({
                'widgets': [self._widget_to_dict(w) for w in self.widgets.values()]
            })

        @self.app.route('/api/dashboard/alerts')
        def get_alerts():
            return jsonify({
                'alerts': [self._alert_to_dict(a) for a in self.alerts.values()]
            })

        @self.app.route('/api/dashboard/metrics')
        def get_metrics():
            return jsonify(self.realtime_data)

        @self.app.route('/api/dashboard/widgets', methods=['POST'])
        def create_widget():
            data = request.json
            widget = DashboardWidget(
                widget_id=data['widget_id'],
                widget_type=data['widget_type'],
                title=data['title'],
                position=data['position'],
                size=data['size'],
                config=data.get('config', {}),
                data_source=data.get('data_source', '')
            )
            self.widgets[widget.widget_id] = widget
            return jsonify({'status': 'success'})

        @self.app.route('/api/dashboard/widgets/<widget_id>', methods=['DELETE'])
        def delete_widget(widget_id):
            if widget_id in self.widgets:
                del self.widgets[widget_id]
                return jsonify({'status': 'success'})
            return jsonify({'error': 'Widget not found'}), 404

    def _setup_socket_events(self):
        """Setup WebSocket events"""

        @self.socketio.on('connect')
        def handle_connect():
            self.connected_clients.add(request.sid)
            emit('dashboard_init', {
                'widgets': [self._widget_to_dict(w) for w in self.widgets.values()],
                'alerts': [self._alert_to_dict(a) for a in self.alerts.values()]
            })

        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.connected_clients.discard(request.sid)

        @self.socketio.on('widget_update')
        def handle_widget_update(data):
            widget_id = data['widget_id']
            if widget_id in self.widgets:
                # Update widget configuration
                widget = self.widgets[widget_id]
                widget.config.update(data.get('config', {}))
                emit('widget_updated', {'widget_id': widget_id})

    def _start_background_tasks(self):
        """Start background dashboard tasks"""
        # Real-time data updates
        threading.Thread(target=self._realtime_data_updater, daemon=True).start()

        # Alert monitoring
        threading.Thread(target=self._alert_monitor, daemon=True).start()

        # Widget data refresh
        threading.Thread(target=self._widget_data_refresher, daemon=True).start()

    def _realtime_data_updater(self):
        """Update real-time dashboard data"""
        while True:
            try:
                # Get data from analytics engine
                from ..analytics.analytics_engine import analytics_engine
                self.realtime_data = analytics_engine.real_time_metrics()

                # Broadcast to connected clients
                if self.connected_clients:
                    self.socketio.emit('realtime_update', self.realtime_data)

            except Exception as e:
                print(f"Realtime data update failed: {e}")

            asyncio.sleep(1)  # Update every second

    def _alert_monitor(self):
        """Monitor and trigger alerts"""
        while True:
            try:
                for alert in self.alerts.values():
                    if not alert.active:
                        # Check alert condition
                        if self._check_alert_condition(alert):
                            alert.active = True
                            self.socketio.emit('alert_triggered', self._alert_to_dict(alert))

                # Reset alerts that are no longer active
                for alert in self.alerts.values():
                    if alert.active and not self._check_alert_condition(alert):
                        alert.active = False
                        self.socketio.emit('alert_resolved', {'alert_id': alert.alert_id})

            except Exception as e:
                print(f"Alert monitoring failed: {e}")

            asyncio.sleep(5)  # Check every 5 seconds

    def _widget_data_refresher(self):
        """Refresh widget data"""
        while True:
            try:
                for widget in self.widgets.values():
                    data = self._get_widget_data(widget)
                    if data:
                        self.socketio.emit('widget_data', {
                            'widget_id': widget.widget_id,
                            'data': data
                        })

            except Exception as e:
                print(f"Widget data refresh failed: {e}")

            asyncio.sleep(10)  # Refresh every 10 seconds

    def _check_alert_condition(self, alert: DashboardAlert) -> bool:
        """Check if alert condition is met"""
        try:
            metric_value = self._get_metric_value(alert.condition)
            if alert.condition.endswith('>'):
                threshold = float(alert.condition.split('>')[1])
                return metric_value > threshold
            elif alert.condition.endswith('<'):
                threshold = float(alert.condition.split('<')[1])
                return metric_value < threshold
            return False
        except:
            return False

    def _get_metric_value(self, condition: str) -> float:
        """Extract metric value from condition"""
        # Parse condition like "server_cpu_usage > 80"
        metric_name = condition.split()[0]
        return self.realtime_data.get(metric_name, 0)

    def _get_widget_data(self, widget: DashboardWidget) -> Optional[Dict]:
        """Get data for a specific widget"""
        try:
            if widget.widget_type == 'chart':
                return self._generate_chart_data(widget)
            elif widget.widget_type == 'metric':
                return self._get_metric_data(widget)
            elif widget.widget_type == 'table':
                return self._get_table_data(widget)
            return None
        except Exception as e:
            print(f"Widget data generation failed: {e}")
            return None

    def _generate_chart_data(self, widget: DashboardWidget) -> Dict:
        """Generate chart data for visualization"""
        chart_type = widget.config.get('chart_type', 'line')
        metric_name = widget.config.get('metric', 'server_cpu_usage')

        # Get historical data (would come from analytics engine)
        from ..analytics.analytics_engine import analytics_engine
        data_points = list(analytics_engine.metrics_store.get(metric_name, []))[-50:]

        if chart_type == 'line':
            return {
                'type': 'line',
                'data': {
                    'x': [datetime.fromtimestamp(p.timestamp).isoformat() for p in data_points],
                    'y': [p.value for p in data_points]
                },
                'title': f"{metric_name.replace('_', ' ').title()} Over Time"
            }
        elif chart_type == 'bar':
            # Aggregate by time buckets
            return {
                'type': 'bar',
                'data': {
                    'x': [f"Bucket {i}" for i in range(len(data_points)//5)],
                    'y': [sum(p.value for p in data_points[i*5:(i+1)*5])/5 for i in range(len(data_points)//5)]
                },
                'title': f"Average {metric_name.replace('_', ' ').title()}"
            }

        return {}

    def _get_metric_data(self, widget: DashboardWidget) -> Dict:
        """Get single metric data"""
        metric_name = widget.config.get('metric', 'server_player_count')
        value = self.realtime_data.get(metric_name, 0)

        return {
            'value': value,
            'unit': widget.config.get('unit', ''),
            'trend': self._calculate_trend(metric_name),
            'status': self._get_metric_status(value, widget.config)
        }

    def _get_table_data(self, widget: DashboardWidget) -> Dict:
        """Get table data for widget"""
        table_type = widget.config.get('table_type', 'servers')

        if table_type == 'servers':
            # Get server status data
            from ..orchestration.server_orchestrator import server_orchestrator
            servers = server_orchestrator.game_servers

            return {
                'headers': ['Server ID', 'Status', 'Players', 'CPU %', 'Memory %'],
                'rows': [[
                    s.server_id,
                    s.status,
                    s.player_count,
                    f"{s.cpu_usage:.1f}",
                    f"{s.memory_usage:.1f}"
                ] for s in servers.values()]
            }

        return {'headers': [], 'rows': []}

    def _calculate_trend(self, metric_name: str) -> str:
        """Calculate metric trend"""
        from ..analytics.analytics_engine import analytics_engine
        metrics = list(analytics_engine.metrics_store.get(metric_name, []))[-10:]

        if len(metrics) < 2:
            return 'stable'

        first_half = sum(m.value for m in metrics[:5]) / 5
        second_half = sum(m.value for m in metrics[5:]) / 5

        if second_half > first_half * 1.05:
            return 'up'
        elif second_half < first_half * 0.95:
            return 'down'
        return 'stable'

    def _get_metric_status(self, value: float, config: Dict) -> str:
        """Get status color for metric"""
        warning_threshold = config.get('warning_threshold', 80)
        critical_threshold = config.get('critical_threshold', 95)

        if value >= critical_threshold:
            return 'critical'
        elif value >= warning_threshold:
            return 'warning'
        return 'normal'

    def _widget_to_dict(self, widget: DashboardWidget) -> Dict:
        """Convert widget to dictionary"""
        return {
            'widget_id': widget.widget_id,
            'widget_type': widget.widget_type,
            'title': widget.title,
            'position': widget.position,
            'size': widget.size,
            'config': widget.config,
            'data_source': widget.data_source
        }

    def _alert_to_dict(self, alert: DashboardAlert) -> Dict:
        """Convert alert to dictionary"""
        return {
            'alert_id': alert.alert_id,
            'condition': alert.condition,
            'threshold': alert.threshold,
            'severity': alert.severity,
            'message': alert.message,
            'active': alert.active
        }

    def add_widget(self, widget_type: str, title: str, position: Dict, size: Dict,
                   config: Dict = None, data_source: str = '') -> str:
        """Add a new widget to the dashboard"""
        widget_id = f"widget_{len(self.widgets)}"
        widget = DashboardWidget(
            widget_id=widget_id,
            widget_type=widget_type,
            title=title,
            position=position,
            size=size,
            config=config or {},
            data_source=data_source
        )
        self.widgets[widget_id] = widget
        return widget_id

    def add_alert(self, condition: str, threshold: float, severity: str, message: str) -> str:
        """Add a new alert"""
        alert_id = f"alert_{len(self.alerts)}"
        alert = DashboardAlert(
            alert_id=alert_id,
            condition=condition,
            threshold=threshold,
            severity=severity,
            message=message,
            active=False
        )
        self.alerts[alert_id] = alert
        return alert_id

    def run(self):
        """Start the dashboard server"""
        print(f"Starting Panel Dashboard on {self.host}:{self.port}")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=False)


# Global dashboard instance
panel_dashboard = PanelDashboard()