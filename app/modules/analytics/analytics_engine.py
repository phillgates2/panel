# app/modules/analytics/analytics_engine.py

"""
Real-time Analytics Dashboard for Panel Application
Implements machine learning insights and live performance metrics
"""

import time
import threading
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import statistics
from collections import defaultdict, deque
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pandas as pd


@dataclass
class MetricData:
    """Time-series metric data point"""
    timestamp: float
    value: float
    labels: Dict[str, str]
    metadata: Dict[str, Any]


@dataclass
class PlayerSession:
    """Player session data"""
    session_id: str
    player_id: str
    server_id: str
    start_time: float
    end_time: Optional[float]
    events: List[Dict]
    metrics: Dict[str, Any]


@dataclass
class ServerMetrics:
    """Server performance metrics"""
    server_id: str
    timestamp: float
    cpu_usage: float
    memory_usage: float
    network_in: float
    network_out: float
    player_count: int
    tick_rate: float
    uptime: float


class AnalyticsEngine:
    """
    Real-time analytics engine with ML-powered insights
    """

    def __init__(self):
        self.metrics_store: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.player_sessions: Dict[str, PlayerSession] = {}
        self.active_alerts: List[Dict] = []
        self.ml_models: Dict[str, Any] = {}
        self.websocket_clients: set = set()
        self.anomaly_detector = None
        self.scaler = StandardScaler()

        # Start background tasks
        self._start_background_tasks()

    def _start_background_tasks(self):
        """Start background analytics tasks"""
        # Anomaly detection training
        threading.Thread(target=self._train_anomaly_detector, daemon=True).start()

        # Metrics aggregation
        threading.Thread(target=self._aggregate_metrics, daemon=True).start()

        # Predictive analytics
        threading.Thread(target=self._run_predictive_analytics, daemon=True).start()

    def record_metric(self, metric_name: str, value: float,
                     labels: Dict[str, str] = None, metadata: Dict[str, Any] = None):
        """Record a metric data point"""
        if labels is None:
            labels = {}
        if metadata is None:
            metadata = {}

        metric_data = MetricData(
            timestamp=time.time(),
            value=value,
            labels=labels,
            metadata=metadata
        )

        self.metrics_store[metric_name].append(metric_data)

        # Real-time alerting
        self._check_alerts(metric_name, metric_data)

        # WebSocket broadcast for real-time dashboard
        self._broadcast_metric(metric_name, metric_data)

    def start_player_session(self, player_id: str, server_id: str) -> str:
        """Start tracking a player session"""
        session_id = f"{player_id}_{int(time.time())}"

        session = PlayerSession(
            session_id=session_id,
            player_id=player_id,
            server_id=server_id,
            start_time=time.time(),
            end_time=None,
            events=[],
            metrics={}
        )

        self.player_sessions[session_id] = session
        return session_id

    def end_player_session(self, session_id: str):
        """End a player session"""
        if session_id in self.player_sessions:
            self.player_sessions[session_id].end_time = time.time()

            # Calculate session metrics
            session = self.player_sessions[session_id]
            duration = session.end_time - session.start_time

            self.record_metric(
                "player_session_duration",
                duration,
                {"player_id": session.player_id, "server_id": session.server_id}
            )

    def record_player_event(self, session_id: str, event_type: str, event_data: Dict):
        """Record a player event"""
        if session_id in self.player_sessions:
            event = {
                "timestamp": time.time(),
                "type": event_type,
                "data": event_data
            }
            self.player_sessions[session_id].events.append(event)

            # Record event metric
            self.record_metric(
                f"player_event_{event_type}",
                1,
                {"session_id": session_id}
            )

    def record_server_metrics(self, server_metrics: ServerMetrics):
        """Record comprehensive server metrics"""
        # Record individual metrics
        metrics = {
            "server_cpu_usage": server_metrics.cpu_usage,
            "server_memory_usage": server_metrics.memory_usage,
            "server_network_in": server_metrics.network_in,
            "server_network_out": server_metrics.network_out,
            "server_player_count": server_metrics.player_count,
            "server_tick_rate": server_metrics.tick_rate,
            "server_uptime": server_metrics.uptime
        }

        for metric_name, value in metrics.items():
            self.record_metric(
                metric_name,
                value,
                {"server_id": server_metrics.server_id}
            )

    def predict_player_behavior(self) -> Dict[str, Any]:
        """
        ML-powered player behavior prediction
        """
        # Analyze player session data
        sessions = list(self.player_sessions.values())

        if len(sessions) < 100:  # Need minimum data
            return {"status": "insufficient_data"}

        # Extract features
        features = []
        for session in sessions[-1000:]:  # Last 1000 sessions
            if session.end_time:
                duration = session.end_time - session.start_time
                event_count = len(session.events)
                features.append([duration, event_count])

        if not features:
            return {"status": "no_completed_sessions"}

        # Simple prediction model (in production, use more sophisticated ML)
        avg_duration = statistics.mean(f[0] for f in features)
        avg_events = statistics.mean(f[1] for f in features)

        # Predict retention
        retention_score = min(avg_events / 10, 1.0)  # Simple heuristic

        return {
            "average_session_duration": avg_duration,
            "average_events_per_session": avg_events,
            "predicted_retention_rate": retention_score,
            "recommendations": self._generate_player_recommendations(avg_duration, avg_events)
        }

    def _generate_player_recommendations(self, avg_duration: float, avg_events: float) -> List[str]:
        """Generate recommendations based on player behavior"""
        recommendations = []

        if avg_duration < 300:  # Less than 5 minutes
            recommendations.append("Consider adding more engaging content early in sessions")
            recommendations.append("Implement tutorial improvements to increase retention")

        if avg_events < 5:
            recommendations.append("Add more interactive elements to increase player engagement")
            recommendations.append("Consider gamification features to boost activity")

        if avg_duration > 3600:  # More than 1 hour
            recommendations.append("Long sessions detected - ensure server stability for extended play")
            recommendations.append("Consider adding break reminders for player health")

        return recommendations

    def real_time_metrics(self) -> Dict[str, Any]:
        """
        Generate real-time performance metrics and dashboard data
        """
        current_time = time.time()
        one_hour_ago = current_time - 3600

        # Aggregate metrics
        dashboard_data = {
            "timestamp": current_time,
            "active_players": self._get_active_player_count(),
            "server_performance": self._get_server_performance(),
            "recent_events": self._get_recent_events(10),
            "alerts": self.active_alerts[-5:],  # Last 5 alerts
            "predictions": self.predict_player_behavior()
        }

        return dashboard_data

    def _get_active_player_count(self) -> int:
        """Get current active player count"""
        active_sessions = [s for s in self.player_sessions.values() if s.end_time is None]
        return len(active_sessions)

    def _get_server_performance(self) -> Dict[str, Any]:
        """Get aggregated server performance metrics"""
        cpu_metrics = list(self.metrics_store.get("server_cpu_usage", []))
        memory_metrics = list(self.metrics_store.get("server_memory_usage", []))
        player_metrics = list(self.metrics_store.get("server_player_count", []))

        if not cpu_metrics:
            return {"status": "no_data"}

        # Calculate averages for last hour
        current_time = time.time()
        recent_cpu = [m.value for m in cpu_metrics if current_time - m.timestamp < 3600]
        recent_memory = [m.value for m in memory_metrics if current_time - m.timestamp < 3600]
        recent_players = [m.value for m in player_metrics if current_time - m.timestamp < 3600]

        return {
            "average_cpu": statistics.mean(recent_cpu) if recent_cpu else 0,
            "average_memory": statistics.mean(recent_memory) if recent_memory else 0,
            "average_players": statistics.mean(recent_players) if recent_players else 0,
            "peak_cpu": max(recent_cpu) if recent_cpu else 0,
            "peak_memory": max(recent_memory) if recent_memory else 0,
            "peak_players": max(recent_players) if recent_players else 0
        }

    def _get_recent_events(self, limit: int = 10) -> List[Dict]:
        """Get recent player events"""
        all_events = []
        for session in self.player_sessions.values():
            for event in session.events[-5:]:  # Last 5 events per session
                all_events.append({
                    "session_id": session.session_id,
                    "player_id": session.player_id,
                    "server_id": session.server_id,
                    **event
                })

        # Sort by timestamp and return most recent
        all_events.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_events[:limit]

    def _check_alerts(self, metric_name: str, metric_data: MetricData):
        """Check for alert conditions"""
        value = metric_data.value
        labels = metric_data.labels

        # Define alert rules
        alert_rules = {
            "server_cpu_usage": {"threshold": 90, "operator": ">", "severity": "high"},
            "server_memory_usage": {"threshold": 95, "operator": ">", "severity": "critical"},
            "server_player_count": {"threshold": 1000, "operator": ">", "severity": "medium"}
        }

        if metric_name in alert_rules:
            rule = alert_rules[metric_name]
            threshold = rule["threshold"]
            operator = rule["operator"]
            severity = rule["severity"]

            alert_triggered = False
            if operator == ">" and value > threshold:
                alert_triggered = True
            elif operator == "<" and value < threshold:
                alert_triggered = True

            if alert_triggered:
                alert = {
                    "timestamp": time.time(),
                    "metric": metric_name,
                    "value": value,
                    "threshold": threshold,
                    "severity": severity,
                    "server_id": labels.get("server_id", "unknown"),
                    "message": f"{metric_name} exceeded threshold: {value} > {threshold}"
                }
                self.active_alerts.append(alert)

    def _train_anomaly_detector(self):
        """Train anomaly detection model"""
        while True:
            try:
                # Collect training data
                training_data = []
                for metric_name, metrics in self.metrics_store.items():
                    if len(metrics) > 100:  # Need sufficient data
                        values = [m.value for m in list(metrics)[-100:]]
                        training_data.append(values)

                if len(training_data) > 10:  # Need multiple metrics
                    # Train Isolation Forest
                    X = np.array(training_data).T
                    self.scaler.fit(X)
                    X_scaled = self.scaler.transform(X)

                    self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
                    self.anomaly_detector.fit(X_scaled)

                    print("Anomaly detector trained successfully")

            except Exception as e:
                print(f"Anomaly detector training failed: {e}")

            time.sleep(3600)  # Retrain every hour

    def _aggregate_metrics(self):
        """Aggregate metrics for dashboard"""
        while True:
            try:
                # Generate hourly aggregations
                dashboard_data = self.real_time_metrics()

                # Store aggregated data (would go to database in production)
                print(f"Metrics aggregated: {len(dashboard_data)} data points")

            except Exception as e:
                print(f"Metrics aggregation failed: {e}")

            time.sleep(60)  # Aggregate every minute

    def _run_predictive_analytics(self):
        """Run predictive analytics"""
        while True:
            try:
                predictions = self.predict_player_behavior()

                if predictions.get("status") != "insufficient_data":
                    print(f"Predictive analytics: Retention rate {predictions.get('predicted_retention_rate', 0):.2%}")

            except Exception as e:
                print(f"Predictive analytics failed: {e}")

            time.sleep(300)  # Run every 5 minutes

    def _broadcast_metric(self, metric_name: str, metric_data: MetricData):
        """Broadcast metric to WebSocket clients"""
        # In production, this would send to connected WebSocket clients
        # For now, just log
        pass

    def get_analytics_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        return {
            "real_time": self.real_time_metrics(),
            "predictions": self.predict_player_behavior(),
            "anomalies": self._detect_anomalies(),
            "trends": self._calculate_trends(),
            "recommendations": self._generate_recommendations()
        }

    def _detect_anomalies(self) -> List[Dict]:
        """Detect anomalies in metrics"""
        anomalies = []

        if self.anomaly_detector is None:
            return anomalies

        try:
            # Check recent metrics for anomalies
            for metric_name, metrics in self.metrics_store.items():
                if len(metrics) > 10:
                    recent_values = [m.value for m in list(metrics)[-10:]]
                    recent_array = np.array(recent_values).reshape(1, -1)

                    scaled_data = self.scaler.transform(recent_array)
                    anomaly_score = self.anomaly_detector.decision_function(scaled_data)

                    if anomaly_score[0] < -0.5:  # Anomaly threshold
                        anomalies.append({
                            "metric": metric_name,
                            "anomaly_score": float(anomaly_score[0]),
                            "recent_values": recent_values,
                            "timestamp": time.time()
                        })

        except Exception as e:
            print(f"Anomaly detection failed: {e}")

        return anomalies

    def _calculate_trends(self) -> Dict[str, Any]:
        """Calculate metric trends"""
        trends = {}

        for metric_name, metrics in self.metrics_store.items():
            if len(metrics) > 20:
                values = [m.value for m in list(metrics)[-20:]]
                if len(values) >= 2:
                    # Simple trend calculation
                    first_half = statistics.mean(values[:10])
                    second_half = statistics.mean(values[10:])

                    if second_half > first_half * 1.1:
                        trend = "increasing"
                    elif second_half < first_half * 0.9:
                        trend = "decreasing"
                    else:
                        trend = "stable"

                    trends[metric_name] = {
                        "trend": trend,
                        "change_percent": ((second_half - first_half) / first_half) * 100,
                        "current_average": second_half
                    }

        return trends

    def _generate_recommendations(self) -> List[str]:
        """Generate analytics-based recommendations"""
        recommendations = []

        # Check server performance
        performance = self._get_server_performance()
        if performance.get("average_cpu", 0) > 80:
            recommendations.append("High CPU usage detected - consider server optimization or scaling")

        if performance.get("average_memory", 0) > 90:
            recommendations.append("High memory usage detected - monitor for memory leaks")

        # Check player engagement
        predictions = self.predict_player_behavior()
        retention = predictions.get("predicted_retention_rate", 0)
        if retention < 0.5:
            recommendations.append("Low player retention detected - review game content and engagement features")

        # Check anomalies
        anomalies = self._detect_anomalies()
        if anomalies:
            recommendations.append(f"Anomalies detected in {len(anomalies)} metrics - investigate unusual patterns")

        return recommendations


# Global analytics engine instance
analytics_engine = AnalyticsEngine()