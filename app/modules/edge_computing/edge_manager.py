# app/modules/edge_computing/edge_manager.py

"""
Distributed Computing & Edge Computing for Panel Application
Global edge computing for gaming with latency optimization
"""

import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import requests
import numpy as np
from sklearn.cluster import KMeans


@dataclass
class EdgeLocation:
    """Edge computing location data"""
    location_id: str
    region: str
    latitude: float
    longitude: float
    capacity: int
    current_load: int
    latency_to_clients: Dict[str, float]


@dataclass
class ServerPlacement:
    """Optimal server placement decision"""
    server_id: str
    edge_location: str
    estimated_latency: float
    capacity_score: float
    cost_score: float
    timestamp: float


class EdgeComputingManager:
    """
    Global edge computing manager for optimal server placement
    """

    def __init__(self):
        self.edge_locations: Dict[str, EdgeLocation] = {}
        self.server_placements: Dict[str, ServerPlacement] = {}
        self.client_locations: Dict[str, Tuple[float, float]] = {}
        self.performance_metrics: Dict[str, List[float]] = {}

        self._initialize_edge_network()
        self._start_background_tasks()

    def _initialize_edge_network(self):
        """Initialize global edge network"""
        # Major cloud regions and edge locations
        edge_network = {
            "us-east-1": {"lat": 39.0, "lon": -77.0, "capacity": 1000},
            "us-west-2": {"lat": 46.0, "lon": -122.0, "capacity": 800},
            "eu-west-1": {"lat": 53.0, "lon": -6.0, "capacity": 900},
            "ap-southeast-1": {"lat": 1.3, "lon": 103.8, "capacity": 700},
            "sa-east-1": {"lat": -23.5, "lon": -46.6, "capacity": 500},
        }

        for region, data in edge_network.items():
            location = EdgeLocation(
                location_id=region,
                region=region,
                latitude=data["lat"],
                longitude=data["lon"],
                capacity=data["capacity"],
                current_load=0,
                latency_to_clients={}
            )
            self.edge_locations[region] = location

    def _start_background_tasks(self):
        """Start background edge computing tasks"""
        threading.Thread(target=self._latency_monitor, daemon=True).start()
        threading.Thread(target=self._capacity_optimizer, daemon=True).start()

    def optimize_server_placement(self, server_id: str, game_type: str,
                                 player_locations: List[Tuple[float, float]]) -> ServerPlacement:
        """
        AI-driven server placement for minimal latency
        """
        # Calculate centroid of player locations
        if player_locations:
            lats, lons = zip(*player_locations)
            centroid_lat = sum(lats) / len(lats)
            centroid_lon = sum(lons) / len(lons)
        else:
            centroid_lat, centroid_lon = 39.0, -77.0  # Default to US East

        # Find optimal edge location
        optimal_location = self._find_optimal_location(centroid_lat, centroid_lon)

        # Calculate estimated latency
        estimated_latency = self._calculate_latency(centroid_lat, centroid_lon,
                                                   optimal_location.latitude,
                                                   optimal_location.longitude)

        # Create placement decision
        placement = ServerPlacement(
            server_id=server_id,
            edge_location=optimal_location.location_id,
            estimated_latency=estimated_latency,
            capacity_score=self._calculate_capacity_score(optimal_location),
            cost_score=self._calculate_cost_score(optimal_location),
            timestamp=time.time()
        )

        self.server_placements[server_id] = placement
        return placement

    def _find_optimal_location(self, target_lat: float, target_lon: float) -> EdgeLocation:
        """Find optimal edge location for given coordinates"""
        min_distance = float('inf')
        optimal_location = None

        for location in self.edge_locations.values():
            distance = self._haversine_distance(target_lat, target_lon,
                                              location.latitude, location.longitude)

            # Consider capacity and current load
            capacity_factor = 1 - (location.current_load / location.capacity)
            effective_distance = distance / capacity_factor

            if effective_distance < min_distance:
                min_distance = effective_distance
                optimal_location = location

        return optimal_location

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate haversine distance between two points"""
        R = 6371  # Earth's radius in kilometers

        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)

        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

        return R * c

    def _calculate_latency(self, client_lat: float, client_lon: float,
                          server_lat: float, server_lon: float) -> float:
        """Calculate estimated latency based on distance"""
        distance = self._haversine_distance(client_lat, client_lon, server_lat, server_lon)

        # Rough latency estimation: ~1ms per 100km
        base_latency = distance / 100

        # Add network overhead
        network_latency = 10  # Base network latency

        return base_latency + network_latency

    def _calculate_capacity_score(self, location: EdgeLocation) -> float:
        """Calculate capacity score (0-1, higher is better)"""
        return 1 - (location.current_load / location.capacity)

    def _calculate_cost_score(self, location: EdgeLocation) -> float:
        """Calculate cost score (0-1, lower cost is better)"""
        # Cost varies by region (simplified)
        region_costs = {
            "us-east-1": 0.8,
            "us-west-2": 0.7,
            "eu-west-1": 0.9,
            "ap-southeast-1": 0.6,
            "sa-east-1": 0.5
        }

        base_cost = region_costs.get(location.region, 0.8)
        return 1 - base_cost  # Invert so higher score = lower cost

    def _latency_monitor(self):
        """Monitor latency between edge locations and clients"""
        while True:
            try:
                # Perform latency tests to key locations
                for location in self.edge_locations.values():
                    # Simulate latency measurements
                    latency_samples = np.random.normal(50, 10, 10)  # Mock data
                    avg_latency = np.mean(latency_samples)

                    self.performance_metrics.setdefault(location.location_id, []).append(avg_latency)

                    # Keep only last 100 measurements
                    if len(self.performance_metrics[location.location_id]) > 100:
                        self.performance_metrics[location.location_id] = self.performance_metrics[location.location_id][-100:]

            except Exception as e:
                print(f"Latency monitoring failed: {e}")

            time.sleep(60)  # Monitor every minute

    def _capacity_optimizer(self):
        """Optimize capacity allocation across edge locations"""
        while True:
            try:
                # Analyze load distribution
                total_capacity = sum(loc.capacity for loc in self.edge_locations.values())
                total_load = sum(loc.current_load for loc in self.edge_locations.values())

                utilization_rate = total_load / total_capacity if total_capacity > 0 else 0

                # Scale capacity if needed
                if utilization_rate > 0.8:
                    print("High utilization detected - consider scaling capacity")
                elif utilization_rate < 0.3:
                    print("Low utilization detected - consider reducing capacity")

            except Exception as e:
                print(f"Capacity optimization failed: {e}")

            time.sleep(300)  # Optimize every 5 minutes

    def get_edge_network_status(self) -> Dict[str, Any]:
        """Get comprehensive edge network status"""
        return {
            "locations": [{
                "id": loc.location_id,
                "region": loc.region,
                "capacity": loc.capacity,
                "current_load": loc.current_load,
                "utilization": loc.current_load / loc.capacity if loc.capacity > 0 else 0
            } for loc in self.edge_locations.values()],
            "server_placements": [{
                "server_id": p.server_id,
                "location": p.edge_location,
                "latency": p.estimated_latency,
                "capacity_score": p.capacity_score,
                "cost_score": p.cost_score
            } for p in self.server_placements.values()],
            "performance_metrics": self.performance_metrics
        }


# Global edge computing manager
edge_computing_manager = EdgeComputingManager()