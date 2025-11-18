"""
API endpoints for monitoring dashboard data.
Provides real-time metrics and alert data for the monitoring system.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from monitoring_system import ServerMetrics, ServerAlert
from sqlalchemy import desc, func
from app import db

# Create API blueprint
api_bp = Blueprint('api_monitoring', __name__, url_prefix='/api/monitoring')

@api_bp.route('/dashboard/metrics')
def get_dashboard_metrics():
    """Get aggregated metrics for the monitoring dashboard."""
    try:
        # Get recent metrics (last 2 hours for charts)
        since = datetime.utcnow() - timedelta(hours=2)
        
        # CPU and Memory timeline (every 5 minutes)
        cpu_timeline = db.session.query(
            ServerMetrics.timestamp,
            func.avg(ServerMetrics.cpu_usage).label('avg_cpu')
        ).filter(
            ServerMetrics.timestamp >= since
        ).group_by(
            func.strftime('%Y-%m-%d %H:%M', ServerMetrics.timestamp)
        ).order_by(ServerMetrics.timestamp).all()
        
        memory_timeline = db.session.query(
            ServerMetrics.timestamp,
            func.avg(ServerMetrics.memory_percentage).label('avg_memory')
        ).filter(
            ServerMetrics.timestamp >= since
        ).group_by(
            func.strftime('%Y-%m-%d %H:%M', ServerMetrics.timestamp)
        ).order_by(ServerMetrics.timestamp).all()
        
        # Player timeline
        player_timeline = db.session.query(
            ServerMetrics.timestamp,
            func.sum(ServerMetrics.player_count).label('total_players')
        ).filter(
            ServerMetrics.timestamp >= since
        ).group_by(
            func.strftime('%Y-%m-%d %H:%M', ServerMetrics.timestamp)
        ).order_by(ServerMetrics.timestamp).all()
        
        # Server distribution
        total_servers = db.session.query(func.distinct(ServerMetrics.server_id)).count()
        
        # Get latest metrics per server to count online/offline
        latest_metrics = db.session.query(
            ServerMetrics.server_id,
            ServerMetrics.is_online,
            func.max(ServerMetrics.timestamp).label('latest')
        ).group_by(ServerMetrics.server_id).subquery()
        
        online_count = db.session.query(ServerMetrics).join(
            latest_metrics,
            (ServerMetrics.server_id == latest_metrics.c.server_id) &
            (ServerMetrics.timestamp == latest_metrics.c.latest)
        ).filter(ServerMetrics.is_online == True).count()
        
        offline_count = total_servers - online_count
        
        # Format timeline data
        cpu_data = {
            'labels': [m.timestamp.isoformat() for m in cpu_timeline],
            'data': [float(m.avg_cpu or 0) for m in cpu_timeline]
        }
        
        memory_data = {
            'labels': [m.timestamp.isoformat() for m in memory_timeline],
            'data': [float(m.avg_memory or 0) for m in memory_timeline]
        }
        
        player_data = {
            'labels': [m.timestamp.isoformat() for m in player_timeline],
            'data': [int(m.total_players or 0) for m in player_timeline]
        }
        
        return jsonify({
            'success': True,
            'metrics': {
                'cpu_timeline': cpu_data,
                'memory_timeline': memory_data,
                'player_timeline': player_data,
                'online_servers': online_count,
                'offline_servers': offline_count,
                'total_servers': total_servers
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching dashboard metrics: {str(e)}'
        }), 500

@api_bp.route('/server/<int:server_id>/metrics')
def get_server_metrics(server_id):
    """Get detailed metrics for a specific server."""
    try:
        # Get time range from query params
        hours = int(request.args.get('hours', 24))
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get metrics for the server
        metrics = db.session.query(ServerMetrics).filter(
            ServerMetrics.server_id == server_id,
            ServerMetrics.timestamp >= since
        ).order_by(ServerMetrics.timestamp).all()
        
        # Format metrics data
        metrics_data = []
        for m in metrics:
            metrics_data.append({
                'timestamp': m.timestamp.isoformat(),
                'cpu_usage': float(m.cpu_usage or 0),
                'memory_percentage': float(m.memory_percentage or 0),
                'memory_used_mb': float(m.memory_used_mb or 0),
                'disk_usage': float(m.disk_usage or 0),
                'network_in_mb': float(m.network_in_mb or 0),
                'network_out_mb': float(m.network_out_mb or 0),
                'player_count': int(m.player_count or 0),
                'ping_ms': int(m.ping_ms or 0),
                'is_online': bool(m.is_online),
                'map_name': m.map_name,
                'game_mode': m.game_mode
            })
        
        return jsonify({
            'success': True,
            'metrics': metrics_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching server metrics: {str(e)}'
        }), 500

@api_bp.route('/server/<int:server_id>/alerts')
def get_server_alerts(server_id):
    """Get recent alerts for a specific server."""
    try:
        # Get recent alerts (last 24 hours)
        since = datetime.utcnow() - timedelta(hours=24)
        
        alerts = db.session.query(ServerAlert).filter(
            ServerAlert.server_id == server_id,
            ServerAlert.triggered_at >= since
        ).order_by(desc(ServerAlert.triggered_at)).limit(50).all()
        
        # Format alerts data
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'id': alert.id,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'message': alert.message,
                'triggered_at': alert.triggered_at.isoformat(),
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                'is_resolved': bool(alert.resolved_at)
            })
        
        return jsonify({
            'success': True,
            'alerts': alerts_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching server alerts: {str(e)}'
        }), 500

@api_bp.route('/alerts/recent')
def get_recent_alerts():
    """Get recent alerts across all servers."""
    try:
        # Get recent unresolved alerts
        since = datetime.utcnow() - timedelta(hours=6)
        
        alerts = db.session.query(
            ServerAlert,
            db.session.query(db.text("servers.name")).filter(
                db.text("servers.id = server_alerts.server_id")
            ).scalar_subquery().label('server_name')
        ).filter(
            ServerAlert.triggered_at >= since,
            ServerAlert.resolved_at.is_(None)  # Only unresolved alerts
        ).order_by(desc(ServerAlert.triggered_at)).limit(20).all()
        
        # Format alerts data
        alerts_data = []
        for alert, server_name in alerts:
            alerts_data.append({
                'id': alert.id,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'message': alert.message,
                'triggered_at': alert.triggered_at.isoformat(),
                'server_name': server_name or 'Unknown'
            })
        
        return jsonify({
            'success': True,
            'alerts': alerts_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching recent alerts: {str(e)}'
        }), 500

@api_bp.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """Resolve a specific alert."""
    try:
        alert = db.session.query(ServerAlert).get(alert_id)
        if not alert:
            return jsonify({
                'success': False,
                'message': 'Alert not found'
            }), 404
        
        if alert.resolved_at:
            return jsonify({
                'success': False,
                'message': 'Alert already resolved'
            }), 400
        
        # Mark alert as resolved
        alert.resolved_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alert resolved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error resolving alert: {str(e)}'
        }), 500

@api_bp.route('/system/status')
def get_system_status():
    """Get overall system monitoring status."""
    try:
        # Get current timestamp
        now = datetime.utcnow()
        
        # Get total servers with recent metrics (last 5 minutes)
        recent_threshold = now - timedelta(minutes=5)
        
        # Count servers by status
        total_servers = db.session.query(func.distinct(ServerMetrics.server_id)).count()
        
        # Get latest metrics per server
        latest_metrics_subq = db.session.query(
            ServerMetrics.server_id,
            func.max(ServerMetrics.timestamp).label('latest_timestamp')
        ).group_by(ServerMetrics.server_id).subquery()
        
        # Join to get actual status
        server_statuses = db.session.query(
            ServerMetrics.server_id,
            ServerMetrics.is_online,
            ServerMetrics.timestamp
        ).join(
            latest_metrics_subq,
            (ServerMetrics.server_id == latest_metrics_subq.c.server_id) &
            (ServerMetrics.timestamp == latest_metrics_subq.c.latest_timestamp)
        ).all()
        
        online_servers = sum(1 for s in server_statuses if s.is_online and s.timestamp >= recent_threshold)
        offline_servers = sum(1 for s in server_statuses if not s.is_online or s.timestamp < recent_threshold)
        stale_servers = sum(1 for s in server_statuses if s.timestamp < recent_threshold)
        
        # Get active alerts count
        active_alerts = db.session.query(ServerAlert).filter(
            ServerAlert.resolved_at.is_(None)
        ).count()
        
        # Get total player count
        total_players = db.session.query(
            func.sum(ServerMetrics.player_count)
        ).join(
            latest_metrics_subq,
            (ServerMetrics.server_id == latest_metrics_subq.c.server_id) &
            (ServerMetrics.timestamp == latest_metrics_subq.c.latest_timestamp)
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'status': {
                'total_servers': total_servers,
                'online_servers': online_servers,
                'offline_servers': offline_servers,
                'stale_servers': stale_servers,
                'active_alerts': active_alerts,
                'total_players': int(total_players),
                'last_updated': now.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching system status: {str(e)}'
        }), 500