# app/modules/game_analytics/game_analytics.py

"""
Advanced Game Analytics & Telemetry for Panel Application
Comprehensive game analytics platform with ML insights
"""

import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler


@dataclass
class PlayerLifecycleEvent:
    """Player lifecycle event data"""
    event_id: str
    player_id: str
    event_type: str
    timestamp: float
    game_session: str
    metadata: Dict[str, Any]


@dataclass
class GameMetric:
    """Game performance metric"""
    metric_id: str
    name: str
    value: float
    timestamp: float
    dimensions: Dict[str, str]


class GameAnalyticsPlatform:
    """
    Comprehensive game analytics platform with ML-powered insights
    """

    def __init__(self):
        self.player_events: List[PlayerLifecycleEvent] = []
        self.game_metrics: List[GameMetric] = []
        self.player_profiles: Dict[str, Dict] = {}
        self.retention_model = None
        self.churn_predictor = None

        self._initialize_analytics()

    def _initialize_analytics(self):
        """Initialize analytics models and data structures"""
        # Initialize ML models for player behavior prediction
        self.retention_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.churn_predictor = RandomForestRegressor(n_estimators=100, random_state=42)

    def track_player_event(self, player_id: str, event_type: str,
                          game_session: str, metadata: Dict = None):
        """Track player lifecycle event"""
        event = PlayerLifecycleEvent(
            event_id=f"evt_{int(time.time())}_{player_id}",
            player_id=player_id,
            event_type=event_type,
            timestamp=time.time(),
            game_session=game_session,
            metadata=metadata or {}
        )

        self.player_events.append(event)

        # Update player profile
        self._update_player_profile(player_id, event)

    def record_game_metric(self, name: str, value: float, dimensions: Dict = None):
        """Record game performance metric"""
        metric = GameMetric(
            metric_id=f"met_{int(time.time())}_{name}",
            name=name,
            value=value,
            timestamp=time.time(),
            dimensions=dimensions or {}
        )

        self.game_metrics.append(metric)

    def _update_player_profile(self, player_id: str, event: PlayerLifecycleEvent):
        """Update player profile with new event data"""
        if player_id not in self.player_profiles:
            self.player_profiles[player_id] = {
                "first_seen": event.timestamp,
                "last_seen": event.timestamp,
                "total_sessions": 0,
                "total_events": 0,
                "event_types": set(),
                "game_modes": set(),
                "achievements": set()
            }

        profile = self.player_profiles[player_id]
        profile["last_seen"] = event.timestamp
        profile["total_events"] += 1
        profile["event_types"].add(event.event_type)

        if "game_mode" in event.metadata:
            profile["game_modes"].add(event.metadata["game_mode"])

    def player_lifecycle_analytics(self, player_id: str = None) -> Dict[str, Any]:
        """
        Complete player lifecycle analysis
        """
        if player_id:
            return self._analyze_single_player(player_id)
        else:
            return self._analyze_player_cohort()

    def _analyze_single_player(self, player_id: str) -> Dict[str, Any]:
        """Analyze individual player lifecycle"""
        if player_id not in self.player_profiles:
            return {"error": "Player not found"}

        profile = self.player_profiles[player_id]
        events = [e for e in self.player_events if e.player_id == player_id]

        # Calculate engagement metrics
        session_duration = self._calculate_session_duration(player_id)
        event_frequency = len(events) / max(1, (profile["last_seen"] - profile["first_seen"]) / 86400)  # events per day

        return {
            "player_id": player_id,
            "account_age_days": (profile["last_seen"] - profile["first_seen"]) / 86400,
            "total_events": profile["total_events"],
            "unique_event_types": len(profile["event_types"]),
            "session_duration_avg": session_duration,
            "event_frequency": event_frequency,
            "engagement_score": self._calculate_engagement_score(profile, events)
        }

    def _analyze_player_cohort(self) -> Dict[str, Any]:
        """Analyze player cohort metrics"""
        if not self.player_profiles:
            return {"error": "No player data available"}

        profiles = list(self.player_profiles.values())

        # Cohort analysis
        total_players = len(profiles)
        active_players = len([p for p in profiles if p["last_seen"] > time.time() - 86400 * 7])  # Active in last 7 days
        new_players = len([p for p in profiles if p["first_seen"] > time.time() - 86400 * 7])  # New in last 7 days

        retention_rate = active_players / total_players if total_players > 0 else 0

        return {
            "total_players": total_players,
            "active_players_7d": active_players,
            "new_players_7d": new_players,
            "retention_rate_7d": retention_rate,
            "average_session_duration": self._calculate_average_session_duration(),
            "top_event_types": self._get_top_event_types(),
            "cohort_retention": self._calculate_cohort_retention()
        }

    def _calculate_session_duration(self, player_id: str) -> float:
        """Calculate average session duration for player"""
        sessions = defaultdict(list)

        for event in self.player_events:
            if event.player_id == player_id:
                sessions[event.game_session].append(event.timestamp)

        if not sessions:
            return 0

        durations = []
        for session_events in sessions.values():
            if len(session_events) > 1:
                durations.append(max(session_events) - min(session_events))

        return sum(durations) / len(durations) if durations else 0

    def _calculate_average_session_duration(self) -> float:
        """Calculate average session duration across all players"""
        session_durations = []

        for player_id in self.player_profiles.keys():
            duration = self._calculate_session_duration(player_id)
            if duration > 0:
                session_durations.append(duration)

        return sum(session_durations) / len(session_durations) if session_durations else 0

    def _get_top_event_types(self) -> List[Tuple[str, int]]:
        """Get most common event types"""
        event_counts = defaultdict(int)

        for event in self.player_events:
            event_counts[event.event_type] += 1

        return sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    def _calculate_cohort_retention(self) -> Dict[str, float]:
        """Calculate cohort retention rates"""
        # Simplified cohort analysis
        cohorts = defaultdict(list)

        for player_id, profile in self.player_profiles.items():
            cohort_week = int(profile["first_seen"] / 604800)  # Weekly cohorts
            cohorts[cohort_week].append(profile)

        retention_rates = {}
        for week, players in cohorts.items():
            week_start = week * 604800
            retention_by_day = []

            for day in range(1, 31):  # 30-day retention
                day_timestamp = week_start + (day * 86400)
                retained = len([p for p in players if p["last_seen"] >= day_timestamp])
                retention_rate = retained / len(players) if players else 0
                retention_by_day.append(retention_rate)

            retention_rates[f"week_{week}"] = retention_by_day

        return retention_rates

    def _calculate_engagement_score(self, profile: Dict, events: List[PlayerLifecycleEvent]) -> float:
        """Calculate player engagement score (0-100)"""
        score = 0

        # Base score from event frequency
        days_active = (profile["last_seen"] - profile["first_seen"]) / 86400
        if days_active > 0:
            events_per_day = profile["total_events"] / days_active
            score += min(events_per_day * 10, 40)  # Max 40 points

        # Bonus for event diversity
        unique_events = len(profile["event_types"])
        score += min(unique_events * 5, 30)  # Max 30 points

        # Bonus for recent activity
        days_since_last_seen = (time.time() - profile["last_seen"]) / 86400
        if days_since_last_seen < 1:
            score += 30  # Max 30 points for very recent activity
        elif days_since_last_seen < 7:
            score += 20

        return min(score, 100)

    def competitive_intelligence(self) -> Dict[str, Any]:
        """
        Market and competitor analysis
        """
        # Analyze market trends and competitive positioning
        metrics = self.game_metrics[-1000:]  # Last 1000 metrics

        if not metrics:
            return {"error": "Insufficient metric data"}

        # Performance benchmarking
        avg_performance = {
            "fps": np.mean([m.value for m in metrics if m.name == "fps"]),
            "latency": np.mean([m.value for m in metrics if m.name == "latency"]),
            "uptime": np.mean([m.value for m in metrics if m.name == "uptime"])
        }

        # Market positioning
        market_position = self._calculate_market_position(avg_performance)

        return {
            "performance_benchmarks": avg_performance,
            "market_position": market_position,
            "competitive_advantages": self._identify_competitive_advantages(),
            "market_trends": self._analyze_market_trends()
        }

    def _calculate_market_position(self, performance: Dict) -> str:
        """Calculate market positioning based on performance"""
        score = 0

        if performance.get("fps", 0) > 50:
            score += 30
        elif performance.get("fps", 0) > 30:
            score += 20

        if performance.get("latency", 0) < 50:
            score += 30
        elif performance.get("latency", 0) < 100:
            score += 20

        if performance.get("uptime", 0) > 0.99:
            score += 40

        if score > 80:
            return "market_leader"
        elif score > 60:
            return "strong_competitor"
        elif score > 40:
            return "average_performer"
        else:
            return "needs_improvement"

    def _identify_competitive_advantages(self) -> List[str]:
        """Identify competitive advantages"""
        advantages = []

        # Analyze unique features and performance metrics
        if len(self.player_profiles) > 1000:
            advantages.append("Large player base")

        # Check for advanced features
        if hasattr(self, 'retention_model') and self.retention_model:
            advantages.append("AI-powered player retention")

        # Performance advantages
        recent_metrics = self.game_metrics[-100:]
        if recent_metrics:
            avg_fps = np.mean([m.value for m in recent_metrics if m.name == "fps"])
            if avg_fps > 55:
                advantages.append("Superior performance")

        return advantages

    def _analyze_market_trends(self) -> Dict[str, Any]:
        """Analyze market trends and predictions"""
        # Trend analysis for key metrics
        trends = {}

        for metric_name in ["fps", "latency", "player_count"]:
            metrics = [m for m in self.game_metrics if m.name == metric_name]
            if len(metrics) > 10:
                values = [m.value for m in metrics[-20:]]
                trend = np.polyfit(range(len(values)), values, 1)[0]
                trends[metric_name] = {
                    "current_value": values[-1],
                    "trend_direction": "increasing" if trend > 0 else "decreasing",
                    "trend_magnitude": abs(trend)
                }

        return trends

    def predictive_analytics(self) -> Dict[str, Any]:
        """
        ML-powered predictive analytics
        """
        # Predict player retention and churn
        if len(self.player_profiles) < 50:
            return {"error": "Insufficient data for predictions"}

        # Prepare training data
        features = []
        targets = []

        for player_id, profile in self.player_profiles.items():
            # Feature engineering
            account_age_days = (profile["last_seen"] - profile["first_seen"]) / 86400
            days_since_last_seen = (time.time() - profile["last_seen"]) / 86400
            events_per_day = profile["total_events"] / max(1, account_age_days)

            features.append([
                account_age_days,
                days_since_last_seen,
                events_per_day,
                len(profile["event_types"]),
                len(profile["game_modes"])
            ])

            # Target: likely to return (active in last 7 days)
            targets.append(1 if days_since_last_seen < 7 else 0)

        # Train model
        X = np.array(features)
        y = np.array(targets)

        if len(X) > 10:
            self.retention_model.fit(X, y)

            # Make predictions
            predictions = self.retention_model.predict(X)

            retention_rate = np.mean(predictions)

            return {
                "predicted_retention_rate": retention_rate,
                "model_accuracy": self.retention_model.score(X, y),
                "retention_insights": self._generate_retention_insights(predictions, features)
            }

        return {"error": "Insufficient data for modeling"}

    def _generate_retention_insights(self, predictions: np.ndarray, features: List) -> List[str]:
        """Generate insights from retention predictions"""
        insights = []

        # Analyze feature importance
        high_risk_players = np.where(predictions < 0.3)[0]

        if len(high_risk_players) > 0:
            avg_days_inactive = np.mean([features[i][1] for i in high_risk_players])
            insights.append(f"High-risk players average {avg_days_inactive:.1f} days inactive")

        # Engagement insights
        low_engagement = [i for i, f in enumerate(features) if f[2] < 1]  # Less than 1 event per day
        if len(low_engagement) > len(features) * 0.3:
            insights.append("Significant portion of players have low engagement")

        return insights


# Global game analytics platform
game_analytics_platform = GameAnalyticsPlatform()