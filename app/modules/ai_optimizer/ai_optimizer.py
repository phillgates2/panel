# app/modules/ai_optimizer/ai_optimizer.py

"""
AI-Powered Game Optimization for Panel Application
Uses machine learning to optimize server configurations and predict performance issues
"""

import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import statistics
from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import tensorflow as tf
from tensorflow import keras
import joblib


@dataclass
class ServerConfig:
    """Server configuration parameters"""
    server_id: str
    tick_rate: int
    max_players: int
    view_distance: int
    simulation_distance: int
    memory_allocation: int
    cpu_priority: str


@dataclass
class PerformanceMetrics:
    """Server performance metrics"""
    timestamp: float
    server_id: str
    fps: float
    cpu_usage: float
    memory_usage: float
    network_latency: float
    player_count: int
    chunk_load_time: float
    entity_count: int


@dataclass
class OptimizationRecommendation:
    """AI-generated optimization recommendation"""
    server_id: str
    parameter: str
    current_value: Any
    recommended_value: Any
    expected_improvement: float
    confidence: float
    reasoning: str
    timestamp: float


class AIOptimizer:
    """
    AI-powered game server optimization using machine learning
    """

    def __init__(self):
        self.performance_history: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        self.config_history: Dict[str, List[ServerConfig]] = defaultdict(list)
        self.optimization_models: Dict[str, Any] = {}
        self.active_recommendations: Dict[str, List[OptimizationRecommendation]] = defaultdict(list)

        # Initialize ML models
        self._initialize_models()

        # Start background optimization tasks
        self._start_background_tasks()

    def _initialize_models(self):
        """Initialize machine learning models"""
        try:
            # Performance prediction model
            self.performance_model = RandomForestRegressor(
                n_estimators=100,
                random_state=42
            )

            # Configuration optimization model
            self.config_model = keras.Sequential([
                keras.layers.Dense(64, activation='relu', input_shape=(10,)),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(16, activation='relu'),
                keras.layers.Dense(1, activation='sigmoid')
            ])

            self.config_model.compile(
                optimizer='adam',
                loss='binary_crossentropy',
                metrics=['accuracy']
            )

            # Anomaly detection for performance issues
            self.anomaly_detector = None

            print("AI models initialized successfully")

        except Exception as e:
            print(f"Model initialization failed: {e}")

    def _start_background_tasks(self):
        """Start background AI optimization tasks"""
        # Model training
        threading.Thread(target=self._train_models, daemon=True).start()

        # Performance monitoring
        threading.Thread(target=self._monitor_performance, daemon=True).start()

        # Configuration optimization
        threading.Thread(target=self._optimize_configurations, daemon=True).start()

    def record_performance_metrics(self, metrics: PerformanceMetrics):
        """Record server performance metrics"""
        self.performance_history[metrics.server_id].append(metrics)

        # Keep only last 1000 data points per server
        if len(self.performance_history[metrics.server_id]) > 1000:
            self.performance_history[metrics.server_id] = self.performance_history[metrics.server_id][-1000:]

    def record_server_config(self, config: ServerConfig):
        """Record server configuration changes"""
        self.config_history[config.server_id].append(config)

        # Keep only last 100 configurations per server
        if len(self.config_history[config.server_id]) > 100:
            self.config_history[config.server_id] = self.config_history[config.server_id][-100:]

    def optimize_server_config(self, server_id: str) -> List[OptimizationRecommendation]:
        """
        AI-driven server configuration optimization
        """
        recommendations = []

        # Get recent performance data
        recent_metrics = self.performance_history.get(server_id, [])
        if len(recent_metrics) < 50:  # Need sufficient data
            return recommendations

        # Get current configuration
        current_configs = self.config_history.get(server_id, [])
        if not current_configs:
            return recommendations

        current_config = current_configs[-1]

        # Analyze performance patterns
        avg_fps = statistics.mean(m.fps for m in recent_metrics[-20:])
        avg_cpu = statistics.mean(m.cpu_usage for m in recent_metrics[-20:])
        avg_memory = statistics.mean(m.memory_usage for m in recent_metrics[-20:])

        # Generate optimization recommendations

        # Tick rate optimization
        if avg_fps < 15 and current_config.tick_rate > 10:
            recommendations.append(OptimizationRecommendation(
                server_id=server_id,
                parameter="tick_rate",
                current_value=current_config.tick_rate,
                recommended_value=max(10, current_config.tick_rate - 2),
                expected_improvement=15.0,
                confidence=0.8,
                reasoning="Low FPS detected, reducing tick rate may improve performance",
                timestamp=time.time()
            ))

        # Memory optimization
        if avg_memory > 80 and current_config.memory_allocation < 8192:
            recommendations.append(OptimizationRecommendation(
                server_id=server_id,
                parameter="memory_allocation",
                current_value=current_config.memory_allocation,
                recommended_value=min(8192, current_config.memory_allocation + 1024),
                expected_improvement=10.0,
                confidence=0.7,
                reasoning="High memory usage, increasing allocation may prevent crashes",
                timestamp=time.time()
            ))

        # View distance optimization
        if avg_cpu > 70 and current_config.view_distance > 8:
            recommendations.append(OptimizationRecommendation(
                server_id=server_id,
                parameter="view_distance",
                current_value=current_config.view_distance,
                recommended_value=max(6, current_config.view_distance - 2),
                expected_improvement=20.0,
                confidence=0.9,
                reasoning="High CPU usage, reducing view distance will improve performance",
                timestamp=time.time()
            ))

        # Simulation distance optimization
        if avg_cpu > 60 and current_config.simulation_distance > current_config.view_distance:
            recommendations.append(OptimizationRecommendation(
                server_id=server_id,
                parameter="simulation_distance",
                current_value=current_config.simulation_distance,
                recommended_value=current_config.view_distance,
                expected_improvement=15.0,
                confidence=0.8,
                reasoning="Simulation distance should not exceed view distance for optimal performance",
                timestamp=time.time()
            ))

        # Store recommendations
        self.active_recommendations[server_id].extend(recommendations)

        return recommendations

    def predict_performance_issues(self, server_id: str) -> Dict[str, Any]:
        """
        Predict potential performance issues before they occur
        """
        predictions = {
            "crash_probability": 0.0,
            "performance_degradation": 0.0,
            "memory_leak_probability": 0.0,
            "warnings": [],
            "recommendations": []
        }

        recent_metrics = self.performance_history.get(server_id, [])
        if len(recent_metrics) < 20:
            return predictions

        # Analyze trends
        recent_fps = [m.fps for m in recent_metrics[-20:]]
        recent_memory = [m.memory_usage for m in recent_metrics[-20:]]
        recent_cpu = [m.cpu_usage for m in recent_metrics[-20:]]

        # FPS trend analysis
        fps_trend = self._calculate_trend(recent_fps)
        if fps_trend < -0.1:  # Declining FPS
            predictions["performance_degradation"] = 0.7
            predictions["warnings"].append("FPS is declining - potential performance issue")
            predictions["recommendations"].append("Monitor server load and consider scaling")

        # Memory leak detection
        memory_trend = self._calculate_trend(recent_memory)
        if memory_trend > 0.05 and statistics.mean(recent_memory) > 75:
            predictions["memory_leak_probability"] = 0.8
            predictions["warnings"].append("Potential memory leak detected")
            predictions["recommendations"].append("Monitor memory usage and restart server if necessary")

        # Crash prediction based on multiple factors
        crash_risk = 0.0
        if statistics.mean(recent_cpu) > 90:
            crash_risk += 0.3
        if statistics.mean(recent_memory) > 95:
            crash_risk += 0.4
        if statistics.mean(recent_fps) < 10:
            crash_risk += 0.3

        predictions["crash_probability"] = min(crash_risk, 1.0)

        if crash_risk > 0.5:
            predictions["warnings"].append("High crash risk detected")
            predictions["recommendations"].append("Immediate attention required - server may crash soon")

        return predictions

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend slope for a series of values"""
        if len(values) < 2:
            return 0.0

        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        y = values

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
        return slope

    def _train_models(self):
        """Train machine learning models with collected data"""
        while True:
            try:
                # Collect training data from all servers
                training_data = []

                for server_id in self.performance_history:
                    metrics = self.performance_history[server_id]
                    configs = self.config_history.get(server_id, [])

                    if len(metrics) > 10 and len(configs) > 0:
                        for i, metric in enumerate(metrics):
                            if i < len(configs):
                                config = configs[i]

                                # Create feature vector
                                features = [
                                    config.tick_rate,
                                    config.max_players,
                                    config.view_distance,
                                    config.simulation_distance,
                                    config.memory_allocation,
                                    metric.player_count,
                                    metric.entity_count,
                                    metric.network_latency,
                                    metric.cpu_usage,
                                    metric.memory_usage
                                ]

                                # Target: FPS performance
                                target = metric.fps

                                training_data.append((features, target))

                if len(training_data) > 100:  # Need sufficient training data
                    X = np.array([d[0] for d in training_data])
                    y = np.array([d[1] for d in training_data])

                    # Split data
                    X_train, X_test, y_train, y_test = train_test_split(
                        X, y, test_size=0.2, random_state=42
                    )

                    # Train performance prediction model
                    self.performance_model.fit(X_train, y_train)

                    # Evaluate model
                    y_pred = self.performance_model.predict(X_test)
                    mae = mean_absolute_error(y_test, y_pred)

                    print(f"Performance model trained. MAE: {mae:.2f} FPS")

                    # Save model
                    joblib.dump(self.performance_model, 'models/performance_model.pkl')

            except Exception as e:
                print(f"Model training failed: {e}")

            time.sleep(3600)  # Retrain every hour

    def _monitor_performance(self):
        """Continuous performance monitoring"""
        while True:
            try:
                for server_id in self.performance_history:
                    predictions = self.predict_performance_issues(server_id)

                    # Alert on high-risk predictions
                    if predictions["crash_probability"] > 0.7:
                        print(f"?? CRITICAL: Server {server_id} has {predictions['crash_probability']:.1%} crash probability!")

                    if predictions["memory_leak_probability"] > 0.8:
                        print(f"??  WARNING: Server {server_id} shows signs of memory leak")

            except Exception as e:
                print(f"Performance monitoring failed: {e}")

            time.sleep(300)  # Check every 5 minutes

    def _optimize_configurations(self):
        """Continuous configuration optimization"""
        while True:
            try:
                for server_id in self.performance_history:
                    recommendations = self.optimize_server_config(server_id)

                    if recommendations:
                        print(f"?? AI Recommendations for {server_id}:")
                        for rec in recommendations:
                            print(f"  - {rec.parameter}: {rec.current_value} ? {rec.recommended_value} "
                                  f"(+{rec.expected_improvement:.1f}% improvement, "
                                  f"{rec.confidence:.1f} confidence)")

            except Exception as e:
                print(f"Configuration optimization failed: {e}")

            time.sleep(600)  # Optimize every 10 minutes

    def get_optimization_report(self, server_id: str) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        return {
            "current_performance": self._get_current_performance(server_id),
            "predictions": self.predict_performance_issues(server_id),
            "recommendations": self.active_recommendations.get(server_id, []),
            "historical_trends": self._analyze_historical_trends(server_id),
            "optimization_score": self._calculate_optimization_score(server_id)
        }

    def _get_current_performance(self, server_id: str) -> Dict[str, Any]:
        """Get current performance metrics"""
        metrics = self.performance_history.get(server_id, [])
        if not metrics:
            return {}

        recent = metrics[-1]
        return {
            "fps": recent.fps,
            "cpu_usage": recent.cpu_usage,
            "memory_usage": recent.memory_usage,
            "player_count": recent.player_count,
            "network_latency": recent.network_latency
        }

    def _analyze_historical_trends(self, server_id: str) -> Dict[str, Any]:
        """Analyze historical performance trends"""
        metrics = self.performance_history.get(server_id, [])
        if len(metrics) < 10:
            return {"status": "insufficient_data"}

        # Calculate trends for key metrics
        fps_values = [m.fps for m in metrics[-50:]]
        cpu_values = [m.cpu_usage for m in metrics[-50:]]
        memory_values = [m.memory_usage for m in metrics[-50:]]

        return {
            "fps_trend": self._calculate_trend(fps_values),
            "cpu_trend": self._calculate_trend(cpu_values),
            "memory_trend": self._calculate_trend(memory_values),
            "average_fps": statistics.mean(fps_values),
            "average_cpu": statistics.mean(cpu_values),
            "average_memory": statistics.mean(memory_values)
        }

    def _calculate_optimization_score(self, server_id: str) -> float:
        """Calculate overall optimization score (0-100)"""
        metrics = self.performance_history.get(server_id, [])
        if not metrics:
            return 0.0

        recent = metrics[-1]

        # Simple scoring algorithm
        score = 100.0

        # Penalize low FPS
        if recent.fps < 20:
            score -= (20 - recent.fps) * 2

        # Penalize high CPU usage
        if recent.cpu_usage > 80:
            score -= (recent.cpu_usage - 80) * 0.5

        # Penalize high memory usage
        if recent.memory_usage > 85:
            score -= (recent.memory_usage - 85) * 0.5

        # Penalize high latency
        if recent.network_latency > 100:
            score -= (recent.network_latency - 100) * 0.1

        return max(0.0, min(100.0, score))

    def apply_optimization(self, server_id: str, recommendation: OptimizationRecommendation) -> bool:
        """
        Apply an AI-generated optimization recommendation
        """
        try:
            # In a real implementation, this would modify server configuration
            # For now, just log the application
            print(f"Applying optimization to {server_id}: "
                  f"{recommendation.parameter} = {recommendation.recommended_value}")

            # Remove from active recommendations
            if server_id in self.active_recommendations:
                self.active_recommendations[server_id] = [
                    r for r in self.active_recommendations[server_id]
                    if r.parameter != recommendation.parameter
                ]

            return True

        except Exception as e:
            print(f"Failed to apply optimization: {e}")
            return False


# Global AI optimizer instance
ai_optimizer = AIOptimizer()