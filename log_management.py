"""
Advanced Log Management and Analytics System

Comprehensive log aggregation, parsing, analysis, and visualization system
for ET:Legacy game servers with real-time streaming and alerting.
"""

import re
import json
import gzip
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app import db
from sqlalchemy import func, desc
import threading
import queue
import time
from collections import defaultdict


logs_bp = Blueprint('logs', __name__)


class LogEntry(db.Model):
    """Structured log entries from game servers."""
    __tablename__ = 'log_entry'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    
    # Log metadata
    timestamp = db.Column(db.DateTime, nullable=False)
    log_level = db.Column(db.String(16), nullable=False)  # INFO, WARN, ERROR, DEBUG
    category = db.Column(db.String(64), nullable=False)   # kill, chat, connect, etc.
    
    # Event data
    event_type = db.Column(db.String(64), nullable=False)
    player_name = db.Column(db.String(128), nullable=True)
    player_guid = db.Column(db.String(64), nullable=True)
    target_name = db.Column(db.String(128), nullable=True)
    target_guid = db.Column(db.String(64), nullable=True)
    
    # Content
    message = db.Column(db.Text, nullable=False)
    raw_log = db.Column(db.Text, nullable=False)
    
    # Parsed data (JSON)
    parsed_data = db.Column(db.Text, nullable=True)
    
    # Indexing
    indexed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    server = db.relationship('Server', backref=db.backref('log_entries', lazy='dynamic'))


class LogPattern(db.Model):
    """Log parsing patterns for different event types."""
    __tablename__ = 'log_pattern'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    pattern = db.Column(db.Text, nullable=False)  # Regular expression
    event_type = db.Column(db.String(64), nullable=False)
    category = db.Column(db.String(64), nullable=False)
    
    # Field mappings (JSON)
    field_mappings = db.Column(db.Text, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=100)  # Higher = processed first
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    creator = db.relationship('User')


class LogAlert(db.Model):
    """Alert rules based on log patterns."""
    __tablename__ = 'log_alert'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Alert criteria
    event_type = db.Column(db.String(64), nullable=True)
    log_level = db.Column(db.String(16), nullable=True)
    player_pattern = db.Column(db.String(256), nullable=True)  # Regex for player names
    message_pattern = db.Column(db.String(512), nullable=True)  # Regex for messages
    
    # Threshold settings
    threshold_count = db.Column(db.Integer, default=1)
    threshold_window_minutes = db.Column(db.Integer, default=5)
    
    # Actions
    notify_discord = db.Column(db.Boolean, default=False)
    notify_email = db.Column(db.Boolean, default=False)
    auto_kick = db.Column(db.Boolean, default=False)
    auto_ban = db.Column(db.Boolean, default=False)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    creator = db.relationship('User')


class LogAnalytics(db.Model):
    """Aggregated analytics data from logs."""
    __tablename__ = 'log_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=True)
    
    # Time period
    period_type = db.Column(db.String(16), nullable=False)  # hourly, daily, weekly
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    
    # Metrics (JSON)
    metrics_data = db.Column(db.Text, nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    server = db.relationship('Server')


class LogProcessor:
    """Real-time log processing and analysis system."""
    
    def __init__(self):
        self.processing_active = False
        self.log_queue = queue.Queue()
        self.processor_thread = None
        
        # Compile patterns on startup
        self.compiled_patterns = {}
        self._load_patterns()
        
        # Alert tracking
        self.alert_counters = defaultdict(lambda: defaultdict(int))
        self.last_alert_check = defaultdict(float)
    
    def _load_patterns(self):
        """Load and compile log patterns."""
        try:
            patterns = LogPattern.query.filter_by(is_active=True).order_by(
                LogPattern.priority.desc()
            ).all()
            
            for pattern in patterns:
                try:
                    compiled_regex = re.compile(pattern.pattern, re.IGNORECASE)
                    self.compiled_patterns[pattern.id] = {
                        'pattern': compiled_regex,
                        'event_type': pattern.event_type,
                        'category': pattern.category,
                        'field_mappings': json.loads(pattern.field_mappings),
                        'name': pattern.name
                    }
                except Exception as e:
                    print(f"Error compiling pattern {pattern.name}: {e}")
                    
        except Exception as e:
            print(f"Error loading patterns: {e}")
    
    def start_processing(self):
        """Start the log processing thread."""
        if self.processing_active:
            return
        
        self.processing_active = True
        self.processor_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processor_thread.start()
    
    def stop_processing(self):
        """Stop the log processing thread."""
        self.processing_active = False
        if self.processor_thread:
            self.processor_thread.join()
    
    def queue_log_line(self, server_id, log_line, timestamp=None):
        """Add a log line to the processing queue."""
        if not timestamp:
            timestamp = datetime.now(timezone.utc)
        
        self.log_queue.put({
            'server_id': server_id,
            'log_line': log_line,
            'timestamp': timestamp
        })
    
    def _processing_loop(self):
        """Main log processing loop."""
        while self.processing_active:
            try:
                # Process queued logs
                while not self.log_queue.empty():
                    log_data = self.log_queue.get(timeout=1)
                    self._process_log_line(log_data)
                
                # Check for alerts periodically
                self._check_alert_thresholds()
                
                time.sleep(0.1)  # Small delay to prevent CPU spinning
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Log processing error: {e}")
                time.sleep(1)
    
    def _process_log_line(self, log_data):
        """Process a single log line."""
        server_id = log_data['server_id']
        log_line = log_data['log_line'].strip()
        timestamp = log_data['timestamp']
        
        if not log_line:
            return
        
        # Try to parse with each pattern
        parsed_entry = None
        
        for pattern_id, pattern_info in self.compiled_patterns.items():
            match = pattern_info['pattern'].search(log_line)
            if match:
                parsed_entry = self._extract_log_data(
                    log_line, timestamp, match, pattern_info
                )
                break
        
        # If no pattern matched, create basic entry
        if not parsed_entry:
            parsed_entry = {
                'timestamp': timestamp,
                'log_level': 'INFO',
                'category': 'unknown',
                'event_type': 'unknown',
                'message': log_line,
                'raw_log': log_line,
                'player_name': None,
                'player_guid': None,
                'target_name': None,
                'target_guid': None,
                'parsed_data': None
            }
        
        # Store in database
        try:
            log_entry = LogEntry(
                server_id=server_id,
                **parsed_entry
            )
            db.session.add(log_entry)
            db.session.commit()
            
            # Check alerts for this entry
            self._check_log_alerts(server_id, log_entry)
            
        except Exception as e:
            print(f"Error storing log entry: {e}")
            db.session.rollback()
    
    def _extract_log_data(self, log_line, timestamp, match, pattern_info):
        """Extract structured data from log line using pattern."""
        field_mappings = pattern_info['field_mappings']
        groups = match.groups()
        
        extracted_data = {
            'timestamp': timestamp,
            'log_level': 'INFO',
            'category': pattern_info['category'],
            'event_type': pattern_info['event_type'],
            'message': log_line,
            'raw_log': log_line,
            'player_name': None,
            'player_guid': None,
            'target_name': None,
            'target_guid': None,
            'parsed_data': {}
        }
        
        # Map regex groups to fields
        for field_name, group_index in field_mappings.items():
            try:
                if isinstance(group_index, int) and group_index < len(groups):
                    value = groups[group_index]
                    
                    if field_name in ['player_name', 'target_name']:
                        extracted_data[field_name] = value
                    elif field_name in ['player_guid', 'target_guid']:
                        extracted_data[field_name] = value
                    elif field_name == 'log_level':
                        extracted_data['log_level'] = value.upper()
                    elif field_name == 'message':
                        extracted_data['message'] = value
                    else:
                        extracted_data['parsed_data'][field_name] = value
                        
            except (IndexError, ValueError):
                continue
        
        # Convert parsed_data to JSON
        if extracted_data['parsed_data']:
            extracted_data['parsed_data'] = json.dumps(extracted_data['parsed_data'])
        else:
            extracted_data['parsed_data'] = None
        
        return extracted_data
    
    def _check_log_alerts(self, server_id, log_entry):
        """Check if log entry triggers any alerts."""
        try:
            alerts = LogAlert.query.filter_by(is_active=True).all()
            
            for alert in alerts:
                if self._matches_alert_criteria(log_entry, alert):
                    self._increment_alert_counter(server_id, alert.id)
                    
        except Exception as e:
            print(f"Alert checking error: {e}")
    
    def _matches_alert_criteria(self, log_entry, alert):
        """Check if log entry matches alert criteria."""
        # Check event type
        if alert.event_type and alert.event_type != log_entry.event_type:
            return False
        
        # Check log level
        if alert.log_level and alert.log_level != log_entry.log_level:
            return False
        
        # Check player pattern
        if alert.player_pattern and log_entry.player_name:
            try:
                if not re.search(alert.player_pattern, log_entry.player_name, re.IGNORECASE):
                    return False
            except re.error:
                pass
        
        # Check message pattern
        if alert.message_pattern:
            try:
                if not re.search(alert.message_pattern, log_entry.message, re.IGNORECASE):
                    return False
            except re.error:
                pass
        
        return True
    
    def _increment_alert_counter(self, server_id, alert_id):
        """Increment alert counter and check threshold."""
        alert_key = f"{server_id}:{alert_id}"
        self.alert_counters[alert_key][int(time.time() // 60)] += 1  # Per minute buckets
    
    def _check_alert_thresholds(self):
        """Check alert thresholds and trigger actions."""
        current_time = time.time()
        
        # Only check every 30 seconds
        if current_time - self.last_alert_check.get('global', 0) < 30:
            return
        
        self.last_alert_check['global'] = current_time
        
        try:
            alerts = LogAlert.query.filter_by(is_active=True).all()
            
            for alert in alerts:
                # Check each server for this alert
                for server_id in set(key.split(':')[0] for key in self.alert_counters.keys() 
                                   if key.endswith(f":{alert.id}")):
                    
                    alert_key = f"{server_id}:{alert.id}"
                    
                    # Count events in threshold window
                    window_start = int((current_time - alert.threshold_window_minutes * 60) // 60)
                    window_end = int(current_time // 60)
                    
                    total_count = sum(
                        self.alert_counters[alert_key][minute]
                        for minute in range(window_start, window_end + 1)
                        if minute in self.alert_counters[alert_key]
                    )
                    
                    if total_count >= alert.threshold_count:
                        self._trigger_alert_action(alert, server_id, total_count)
                        
                        # Reset counter to avoid spam
                        self.alert_counters[alert_key].clear()
        
        except Exception as e:
            print(f"Alert threshold checking error: {e}")
    
    def _trigger_alert_action(self, alert, server_id, count):
        """Trigger alert actions."""
        try:
            from app import Server
            server = Server.query.get(server_id)
            
            message = f"Alert '{alert.name}' triggered on {server.name}: {count} events in {alert.threshold_window_minutes} minutes"
            
            # Discord notification
            if alert.notify_discord:
                self._send_discord_alert(alert, server, message)
            
            # Email notification
            if alert.notify_email:
                self._send_email_alert(alert, server, message)
            
            # Auto-moderation actions would go here
            if alert.auto_kick or alert.auto_ban:
                print(f"Auto-moderation triggered: {message}")
                
        except Exception as e:
            print(f"Alert action error: {e}")
    
    def _send_discord_alert(self, alert, server, message):
        """Send Discord webhook alert."""
        try:
            import requests
            import os
            
            webhook_url = os.environ.get('PANEL_DISCORD_WEBHOOK')
            if not webhook_url:
                return
            
            embed = {
                'title': '🚨 Log Alert Triggered',
                'description': message,
                'color': 0xe74c3c,  # Red
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'fields': [
                    {
                        'name': 'Alert',
                        'value': alert.name,
                        'inline': True
                    },
                    {
                        'name': 'Server',
                        'value': server.name,
                        'inline': True
                    }
                ]
            }
            
            payload = {'embeds': [embed]}
            requests.post(webhook_url, json=payload, timeout=10)
            
        except Exception as e:
            print(f"Discord alert error: {e}")
    
    def _send_email_alert(self, alert, server, message):
        """Send email alert (placeholder)."""
        print(f"EMAIL ALERT: {message}")
    
    def get_log_statistics(self, server_id=None, hours=24):
        """Get log statistics for dashboard."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = LogEntry.query.filter(LogEntry.timestamp >= since)
        if server_id:
            query = query.filter(LogEntry.server_id == server_id)
        
        # Event type distribution
        event_stats = db.session.query(
            LogEntry.event_type,
            func.count(LogEntry.id).label('count')
        ).filter(LogEntry.timestamp >= since)
        
        if server_id:
            event_stats = event_stats.filter(LogEntry.server_id == server_id)
        
        event_stats = event_stats.group_by(LogEntry.event_type).all()
        
        # Log level distribution
        level_stats = db.session.query(
            LogEntry.log_level,
            func.count(LogEntry.id).label('count')
        ).filter(LogEntry.timestamp >= since)
        
        if server_id:
            level_stats = level_stats.filter(LogEntry.server_id == server_id)
        
        level_stats = level_stats.group_by(LogEntry.log_level).all()
        
        # Timeline data (hourly buckets)
        timeline_stats = db.session.query(
            func.date_trunc('hour', LogEntry.timestamp).label('hour'),
            func.count(LogEntry.id).label('count')
        ).filter(LogEntry.timestamp >= since)
        
        if server_id:
            timeline_stats = timeline_stats.filter(LogEntry.server_id == server_id)
        
        timeline_stats = timeline_stats.group_by('hour').order_by('hour').all()
        
        return {
            'event_distribution': [(e.event_type, e.count) for e in event_stats],
            'level_distribution': [(l.log_level, l.count) for l in level_stats],
            'timeline': [(t.hour.isoformat(), t.count) for t in timeline_stats],
            'total_entries': query.count()
        }


# Global log processor instance
log_processor = LogProcessor()


@logs_bp.route('/admin/logs/dashboard')
@login_required
def logs_dashboard():
    """Main logs dashboard."""
    if not current_user.is_system_admin:
        return redirect(url_for('dashboard'))
    
    from app import Server
    servers = Server.query.all()
    
    # Get overall statistics
    stats = log_processor.get_log_statistics(hours=24)
    
    return render_template('admin_logs_dashboard.html', 
                         servers=servers, stats=stats)


@logs_bp.route('/admin/logs/server/<int:server_id>')
@login_required
def server_logs(server_id):
    """Server-specific log viewer."""
    from app import Server
    server = Server.query.get_or_404(server_id)
    
    # Check permissions
    if not (current_user.is_system_admin or server.owner_id == current_user.id):
        return redirect(url_for('dashboard'))
    
    # Get recent logs
    logs = LogEntry.query.filter_by(server_id=server_id).order_by(
        desc(LogEntry.timestamp)
    ).limit(500).all()
    
    # Get server statistics
    stats = log_processor.get_log_statistics(server_id=server_id, hours=24)
    
    return render_template('admin_logs_server.html', 
                         server=server, logs=logs, stats=stats)


@logs_bp.route('/admin/logs/patterns', methods=['GET', 'POST'])
@login_required
def manage_patterns():
    """Manage log parsing patterns."""
    if not current_user.is_system_admin:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            pattern = LogPattern(
                name=data['name'],
                pattern=data['pattern'],
                event_type=data['event_type'],
                category=data['category'],
                field_mappings=json.dumps(data['field_mappings']),
                priority=data.get('priority', 100),
                created_by=current_user.id
            )
            
            db.session.add(pattern)
            db.session.commit()
            
            # Reload patterns in processor
            log_processor._load_patterns()
            
            return jsonify({'success': True, 'pattern_id': pattern.id})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    patterns = LogPattern.query.order_by(desc(LogPattern.created_at)).all()
    return render_template('admin_logs_patterns.html', patterns=patterns)


@logs_bp.route('/api/logs/search')
@login_required
def search_logs():
    """Search logs API endpoint."""
    server_id = request.args.get('server_id', type=int)
    query_text = request.args.get('q', '')
    event_type = request.args.get('event_type')
    log_level = request.args.get('log_level')
    player_name = request.args.get('player_name')
    limit = min(request.args.get('limit', 100, type=int), 1000)
    
    # Check permissions
    if server_id:
        from app import Server
        server = Server.query.get_or_404(server_id)
        if not (current_user.is_system_admin or server.owner_id == current_user.id):
            return jsonify({'error': 'Access denied'}), 403
    elif not current_user.is_system_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    # Build query
    query = LogEntry.query
    
    if server_id:
        query = query.filter(LogEntry.server_id == server_id)
    
    if query_text:
        query = query.filter(LogEntry.message.contains(query_text))
    
    if event_type:
        query = query.filter(LogEntry.event_type == event_type)
    
    if log_level:
        query = query.filter(LogEntry.log_level == log_level)
    
    if player_name:
        query = query.filter(LogEntry.player_name.contains(player_name))
    
    # Get results
    logs = query.order_by(desc(LogEntry.timestamp)).limit(limit).all()
    
    results = []
    for log in logs:
        results.append({
            'id': log.id,
            'timestamp': log.timestamp.isoformat(),
            'log_level': log.log_level,
            'category': log.category,
            'event_type': log.event_type,
            'player_name': log.player_name,
            'target_name': log.target_name,
            'message': log.message,
            'server_name': log.server.name if log.server else None
        })
    
    return jsonify({
        'success': True,
        'logs': results,
        'total': len(results)
    })


def start_log_processing():
    """Start the log processing system."""
    log_processor.start_processing()


def stop_log_processing():
    """Stop the log processing system."""
    log_processor.stop_processing()


def ingest_log_file(server_id, file_path):
    """Ingest a log file for processing."""
    try:
        if file_path.endswith('.gz'):
            with gzip.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        
        for line in lines:
            log_processor.queue_log_line(server_id, line.strip())
        
        return len(lines)
        
    except Exception as e:
        print(f"Error ingesting log file {file_path}: {e}")
        return 0