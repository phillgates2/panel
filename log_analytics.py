"""
Advanced Log Analytics and Intelligence System

Provides comprehensive log analysis, pattern detection, anomaly detection,
and intelligent alerting for ET:Legacy game servers with machine learning capabilities.
"""

import re
import time
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app import db
from sqlalchemy import func, desc, Index
import threading
import queue
import hashlib
from dataclasses import dataclass
from typing import List, Optional, Tuple
import statistics


log_analytics_bp = Blueprint('log_analytics', __name__)


class LogEntry(db.Model):
    """Store and index server log entries for analysis."""
    __tablename__ = 'log_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    level = db.Column(db.String(20), nullable=False, index=True)  # INFO, WARN, ERROR, DEBUG
    source = db.Column(db.String(100), nullable=True, index=True)  # Component that generated log
    message = db.Column(db.Text, nullable=False)
    message_hash = db.Column(db.String(64), nullable=False, index=True)  # For deduplication
    raw_line = db.Column(db.Text, nullable=True)  # Original log line
    
    # Parsed fields
    player_id = db.Column(db.String(50), nullable=True, index=True)
    player_name = db.Column(db.String(100), nullable=True, index=True)
    action = db.Column(db.String(50), nullable=True, index=True)  # kill, death, connect, etc.
    weapon = db.Column(db.String(50), nullable=True)
    map_name = db.Column(db.String(100), nullable=True, index=True)
    
    # Analytics fields
    is_anomaly = db.Column(db.Boolean, default=False, index=True)
    anomaly_score = db.Column(db.Float, nullable=True)
    pattern_id = db.Column(db.String(50), nullable=True, index=True)
    processed = db.Column(db.Boolean, default=False, index=True)


class LogPattern(db.Model):
    """Store detected log patterns and their characteristics."""
    __tablename__ = 'log_patterns'
    
    id = db.Column(db.Integer, primary_key=True)
    pattern_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    pattern_template = db.Column(db.Text, nullable=False)  # Regex pattern
    pattern_type = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # Statistics
    first_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    occurrence_count = db.Column(db.Integer, default=1)
    avg_frequency = db.Column(db.Float, nullable=True)  # Messages per hour
    
    # Severity and alerting
    severity = db.Column(db.String(20), default='info')  # info, warning, error, critical
    alert_threshold = db.Column(db.Integer, nullable=True)  # Alert when count exceeds this
    is_benign = db.Column(db.Boolean, default=False)  # User-marked as safe
    is_monitored = db.Column(db.Boolean, default=True)


class LogAnomaly(db.Model):
    """Store detected log anomalies and security events."""
    __tablename__ = 'log_anomalies'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    log_entry_id = db.Column(db.Integer, db.ForeignKey('log_entries.id'), nullable=False)
    
    anomaly_type = db.Column(db.String(50), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, index=True)
    confidence = db.Column(db.Float, nullable=False)  # 0.0 to 1.0
    
    description = db.Column(db.Text, nullable=False)
    detection_method = db.Column(db.String(100), nullable=False)
    
    # Context information
    context_data = db.Column(db.JSON, nullable=True)
    related_entries = db.Column(db.JSON, nullable=True)  # List of related log entry IDs
    
    # Resolution tracking
    is_resolved = db.Column(db.Boolean, default=False, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.String(100), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class LogAlert(db.Model):
    """Store log-based alerts and notifications."""
    __tablename__ = 'log_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, index=True)
    
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Trigger information
    trigger_pattern = db.Column(db.String(200), nullable=True)
    trigger_count = db.Column(db.Integer, nullable=True)
    time_window = db.Column(db.Integer, nullable=True)  # Minutes
    
    # Notification tracking
    is_sent = db.Column(db.Boolean, default=False, index=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    notification_channels = db.Column(db.JSON, nullable=True)  # email, slack, etc.
    
    # Auto-resolution
    auto_resolve = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


@dataclass
class LogParseResult:
    """Result of log parsing operation."""
    level: str
    source: str
    message: str
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    action: Optional[str] = None
    weapon: Optional[str] = None
    map_name: Optional[str] = None
    timestamp: Optional[datetime] = None


class LogParser:
    """Advanced log parser with pattern recognition and field extraction."""
    
    def __init__(self):
        # ET:Legacy log patterns
        self.patterns = {
            'kill': re.compile(r'Kill: (\d+) (\d+) (\d+): (.+?) killed (.+?) by (.+)'),
            'connect': re.compile(r'ClientConnect: (\d+) \[(.+?)\]'),
            'disconnect': re.compile(r'ClientDisconnect: (\d+)'),
            'userinfo': re.compile(r'ClientUserinfoChanged: (\d+) (.+)'),
            'say': re.compile(r'say: (.+?): (.+)'),
            'map_change': re.compile(r'InitGame: .*fs_game\\.*\\g_gametype\\.*\\mapname\\([^\\]+)'),
            'server_start': re.compile(r'------- Server Initialization -------'),
            'server_shutdown': re.compile(r'------- Server Shutdown -------'),
            'rcon_command': re.compile(r'rcon from (.+?): (.+)'),
            'admin_action': re.compile(r'Admin (.+?) executed: (.+)'),
        }
        
        # Security patterns
        self.security_patterns = {
            'brute_force': re.compile(r'Failed login attempt from (.+)'),
            'exploit_attempt': re.compile(r'Potential exploit detected: (.+)'),
            'suspicious_command': re.compile(r'Suspicious command: (.+)'),
            'rate_limit': re.compile(r'Rate limit exceeded for (.+)'),
        }
    
    def parse_log_line(self, line: str, timestamp: datetime = None) -> LogParseResult:
        """Parse a single log line and extract structured data."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        # Default values
        level = 'INFO'
        source = 'game'
        message = line.strip()
        
        # Extract log level if present
        level_match = re.match(r'^\[(\w+)\]', line)
        if level_match:
            level = level_match.group(1).upper()
            line = line[len(level_match.group(0)):].strip()
        
        # Extract timestamp if present
        timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if timestamp_match:
            try:
                timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                timestamp = timestamp.replace(tzinfo=timezone.utc)
                line = line[len(timestamp_match.group(0)):].strip()
            except ValueError:
                pass
        
        result = LogParseResult(
            level=level,
            source=source,
            message=message,
            timestamp=timestamp
        )
        
        # Try to match specific patterns
        for pattern_name, pattern in self.patterns.items():
            match = pattern.search(line)
            if match:
                if pattern_name == 'kill':
                    result.player_id = match.group(1)
                    result.player_name = match.group(4)
                    result.action = 'kill'
                    result.weapon = match.group(6)
                elif pattern_name == 'connect':
                    result.player_id = match.group(1)
                    result.action = 'connect'
                elif pattern_name == 'disconnect':
                    result.player_id = match.group(1)
                    result.action = 'disconnect'
                elif pattern_name == 'map_change':
                    result.map_name = match.group(1)
                    result.action = 'map_change'
                    result.source = 'server'
                elif pattern_name == 'rcon_command':
                    result.source = 'rcon'
                    result.action = 'admin_command'
                break
        
        return result


class AnomalyDetector:
    """Machine learning-based anomaly detection for logs."""
    
    def __init__(self):
        self.baseline_stats = defaultdict(dict)
        self.pattern_frequencies = defaultdict(int)
        self.time_series_data = defaultdict(lambda: deque(maxlen=1440))  # 24 hours of minutes
        
    def update_baseline(self, server_id: int, log_entries: List[LogEntry]):
        """Update baseline statistics for a server."""
        if not log_entries:
            return
            
        # Calculate message frequency by hour
        hourly_counts = defaultdict(int)
        for entry in log_entries:
            hour_key = entry.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour_key] += 1
            
        # Update baseline stats
        if hourly_counts:
            self.baseline_stats[server_id]['avg_messages_per_hour'] = statistics.mean(hourly_counts.values())
            self.baseline_stats[server_id]['std_messages_per_hour'] = statistics.stdev(hourly_counts.values()) if len(hourly_counts) > 1 else 0
            
        # Update pattern frequencies
        for entry in log_entries:
            pattern_key = f"{entry.level}_{entry.source}_{entry.action or 'unknown'}"
            self.pattern_frequencies[f"{server_id}_{pattern_key}"] += 1
    
    def detect_anomalies(self, server_id: int, recent_entries: List[LogEntry]) -> List[Tuple[LogEntry, float, str]]:
        """Detect anomalies in recent log entries."""
        anomalies = []
        
        if not recent_entries:
            return anomalies
            
        # Check for message volume anomalies
        current_hour_count = len(recent_entries)
        baseline = self.baseline_stats.get(server_id, {})
        
        if baseline and 'avg_messages_per_hour' in baseline:
            avg_rate = baseline['avg_messages_per_hour']
            std_rate = baseline['std_messages_per_hour']
            
            # Statistical anomaly detection (3-sigma rule)
            if abs(current_hour_count - avg_rate) > 3 * std_rate:
                confidence = min(abs(current_hour_count - avg_rate) / (std_rate + 1), 1.0)
                anomalies.append((
                    recent_entries[0], 
                    confidence,
                    f"Unusual message volume: {current_hour_count} vs avg {avg_rate:.1f}"
                ))
        
        # Check for unusual patterns
        for entry in recent_entries:
            pattern_key = f"{server_id}_{entry.level}_{entry.source}_{entry.action or 'unknown'}"
            
            # New pattern detection
            if self.pattern_frequencies[pattern_key] == 0:
                anomalies.append((entry, 0.7, "Previously unseen log pattern"))
            
            # Frequency-based anomaly
            elif entry.level == 'ERROR' and self.pattern_frequencies[pattern_key] < 5:
                anomalies.append((entry, 0.8, "Rare error pattern"))
        
        return anomalies


class LogProcessor:
    """Real-time log processing and analysis engine."""
    
    def __init__(self):
        self.parser = LogParser()
        self.anomaly_detector = AnomalyDetector()
        self.processing_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None
        
    def start_processing(self, app=None):
        """Start the background log processing thread."""
        if self.is_running:
            return
            
        self.is_running = True
        self.app = app
        self.worker_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.worker_thread.start()
    
    def stop_processing(self):
        """Stop the background processing."""
        self.is_running = False
        
    def ingest_log_line(self, server_id: int, line: str):
        """Add a log line to the processing queue."""
        self.processing_queue.put((server_id, line))
    
    def _process_loop(self):
        """Main processing loop for log analysis."""
        while self.is_running:
            try:
                if self.app:
                    with self.app.app_context():
                        # Process queued logs
                        while not self.processing_queue.empty():
                            server_id, line = self.processing_queue.get_nowait()
                            self._process_log_line(server_id, line)
                else:
                    # Skip processing without app context
                    time.sleep(30)
                    continue
                
                # Update anomaly detection baselines every 5 minutes
                self._update_baselines()
                
                # Check for new anomalies
                self._detect_anomalies()
                
                time.sleep(30)  # Process every 30 seconds
                
            except Exception as e:
                print(f"Log processing error: {e}")
                time.sleep(5)
    
    def _process_log_line(self, server_id: int, line: str):
        """Process a single log line."""
        try:
            # Parse the log line
            parsed = self.parser.parse_log_line(line)
            
            # Create message hash for deduplication
            message_hash = hashlib.sha256(
                f"{parsed.level}_{parsed.source}_{parsed.message}".encode()
            ).hexdigest()
            
            # Check if we've seen this exact message recently (last hour)
            recent_duplicate = db.session.query(LogEntry).filter(
                LogEntry.server_id == server_id,
                LogEntry.message_hash == message_hash,
                LogEntry.timestamp > datetime.now(timezone.utc) - timedelta(hours=1)
            ).first()
            
            if recent_duplicate:
                return  # Skip duplicate
            
            # Create log entry
            entry = LogEntry(
                server_id=server_id,
                timestamp=parsed.timestamp,
                level=parsed.level,
                source=parsed.source,
                message=parsed.message,
                message_hash=message_hash,
                raw_line=line,
                player_id=parsed.player_id,
                player_name=parsed.player_name,
                action=parsed.action,
                weapon=parsed.weapon,
                map_name=parsed.map_name
            )
            
            db.session.add(entry)
            db.session.commit()
            
        except Exception as e:
            print(f"Error processing log line: {e}")
            db.session.rollback()
    
    def _update_baselines(self):
        """Update anomaly detection baselines."""
        try:
            # Get active servers
            from app import Server
            servers = db.session.query(Server).all()
            
            for server in servers:
                # Get recent log entries for baseline calculation
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
                recent_entries = db.session.query(LogEntry).filter(
                    LogEntry.server_id == server.id,
                    LogEntry.timestamp > cutoff_time
                ).all()
                
                self.anomaly_detector.update_baseline(server.id, recent_entries)
                
        except Exception as e:
            print(f"Error updating baselines: {e}")
    
    def _detect_anomalies(self):
        """Detect and record new anomalies."""
        try:
            from app import Server
            servers = db.session.query(Server).all()
            
            for server in servers:
                # Get recent unprocessed entries
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
                recent_entries = db.session.query(LogEntry).filter(
                    LogEntry.server_id == server.id,
                    LogEntry.timestamp > cutoff_time,
                    LogEntry.processed == False
                ).all()
                
                if not recent_entries:
                    continue
                
                # Detect anomalies
                anomalies = self.anomaly_detector.detect_anomalies(server.id, recent_entries)
                
                for entry, confidence, description in anomalies:
                    # Create anomaly record
                    anomaly = LogAnomaly(
                        server_id=server.id,
                        log_entry_id=entry.id,
                        anomaly_type='statistical',
                        severity='warning' if confidence < 0.8 else 'critical',
                        confidence=confidence,
                        description=description,
                        detection_method='statistical_analysis'
                    )
                    
                    db.session.add(anomaly)
                    
                    # Mark entry as anomaly
                    entry.is_anomaly = True
                    entry.anomaly_score = confidence
                
                # Mark entries as processed
                for entry in recent_entries:
                    entry.processed = True
                
                db.session.commit()
                
        except Exception as e:
            print(f"Error detecting anomalies: {e}")
            db.session.rollback()


# Global log processor instance
log_processor = LogProcessor()


# Routes for log analytics dashboard
@log_analytics_bp.route('/admin/logs/analytics')
@login_required
def log_analytics_dashboard():
    """Main log analytics dashboard."""
    if not current_user.is_system_admin:
        return redirect(url_for('dashboard'))
    
    from app import Server
    
    # Get servers and their recent log statistics
    servers = db.session.query(Server).all()
    server_stats = []
    
    for server in servers:
        # Recent log count (last 24 hours)
        recent_count = db.session.query(func.count(LogEntry.id)).filter(
            LogEntry.server_id == server.id,
            LogEntry.timestamp > datetime.now(timezone.utc) - timedelta(hours=24)
        ).scalar()
        
        # Anomaly count
        anomaly_count = db.session.query(func.count(LogAnomaly.id)).filter(
            LogAnomaly.server_id == server.id,
            LogAnomaly.is_resolved == False
        ).scalar()
        
        # Alert count
        alert_count = db.session.query(func.count(LogAlert.id)).filter(
            LogAlert.server_id == server.id,
            LogAlert.resolved_at.is_(None)
        ).scalar()
        
        server_stats.append({
            'server': server,
            'recent_logs': recent_count,
            'anomalies': anomaly_count,
            'alerts': alert_count
        })
    
    return render_template('admin_log_analytics.html', server_stats=server_stats)


@log_analytics_bp.route('/admin/logs/server/<int:server_id>')
@login_required
def server_log_analysis(server_id):
    """Detailed log analysis for a specific server."""
    if not current_user.is_system_admin:
        return redirect(url_for('dashboard'))
    
    from app import Server
    server = db.session.query(Server).get_or_404(server_id)
    
    # Get time range from query params
    hours = int(request.args.get('hours', 24))
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Recent log entries
    recent_logs = db.session.query(LogEntry).filter(
        LogEntry.server_id == server_id,
        LogEntry.timestamp > cutoff_time
    ).order_by(desc(LogEntry.timestamp)).limit(1000).all()
    
    # Anomalies
    anomalies = db.session.query(LogAnomaly).filter(
        LogAnomaly.server_id == server_id,
        LogAnomaly.created_at > cutoff_time
    ).order_by(desc(LogAnomaly.created_at)).all()
    
    # Alerts
    alerts = db.session.query(LogAlert).filter(
        LogAlert.server_id == server_id,
        LogAlert.created_at > cutoff_time
    ).order_by(desc(LogAlert.created_at)).all()
    
    return render_template('server_log_analysis.html', 
                         server=server, 
                         recent_logs=recent_logs,
                         anomalies=anomalies,
                         alerts=alerts,
                         hours=hours)


def start_log_analytics(app=None):
    """Start the log analytics system."""
    log_processor.start_processing(app)


def stop_log_analytics():
    """Stop the log analytics system."""
    log_processor.stop_processing()


# Create database indexes for better performance
def create_log_indexes():
    """Create database indexes for log analytics performance."""
    try:
        # Composite indexes for common queries
        index1 = Index('idx_log_server_timestamp', LogEntry.server_id, LogEntry.timestamp)
        index2 = Index('idx_log_level_timestamp', LogEntry.level, LogEntry.timestamp)
        index3 = Index('idx_anomaly_server_resolved', LogAnomaly.server_id, LogAnomaly.is_resolved)
        index4 = Index('idx_alert_server_resolved', LogAlert.server_id, LogAlert.resolved_at)
        
        # Create indexes if they don't exist
        for index in [index1, index2, index3, index4]:
            try:
                index.create(db.engine, checkfirst=True)
            except Exception:
                pass  # Index might already exist
                
    except Exception as e:
        print(f"Error creating log indexes: {e}")