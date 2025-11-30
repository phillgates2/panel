"""
Multi-Server Management Dashboard and Cluster Orchestration System

Provides centralized management, deployment, and orchestration capabilities
for multiple ET:Legacy game servers with load balancing and failover support.
"""

import socket
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List, Tuple

import paramiko
from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc

from app import db

multi_server_bp = Blueprint("multi_server", __name__)


class ServerStatus(Enum):
    """Server status enumeration."""

    ONLINE = "online"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DeploymentStatus(Enum):
    """Deployment status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ServerCluster(db.Model):
    """Define server clusters for organized management."""

    __tablename__ = "server_clusters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    # Cluster configuration
    load_balancer_enabled = db.Column(db.Boolean, default=False)
    auto_failover_enabled = db.Column(db.Boolean, default=False)
    max_servers = db.Column(db.Integer, default=10)

    # Geographic and networking
    region = db.Column(db.String(50), nullable=True)
    datacenter = db.Column(db.String(100), nullable=True)
    network_zone = db.Column(db.String(50), nullable=True)

    # Management settings
    auto_scaling_enabled = db.Column(db.Boolean, default=False)
    min_servers = db.Column(db.Integer, default=1)
    target_cpu_utilization = db.Column(db.Float, default=70.0)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ServerNode(db.Model):
    """Extended server information for cluster management."""

    __tablename__ = "server_nodes"

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(
        db.Integer, db.ForeignKey("server.id"), nullable=False, unique=True
    )
    cluster_id = db.Column(
        db.Integer, db.ForeignKey("server_clusters.id"), nullable=True
    )

    # Physical/Virtual server details
    hostname = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    ssh_port = db.Column(db.Integer, default=22)
    ssh_username = db.Column(db.String(100), nullable=True)
    ssh_key_path = db.Column(db.String(500), nullable=True)

    # Server specifications
    cpu_cores = db.Column(db.Integer, nullable=True)
    memory_gb = db.Column(db.Integer, nullable=True)
    disk_gb = db.Column(db.Integer, nullable=True)
    network_bandwidth_mbps = db.Column(db.Integer, nullable=True)

    # Management settings
    auto_restart_enabled = db.Column(db.Boolean, default=True)
    backup_enabled = db.Column(db.Boolean, default=True)
    monitoring_enabled = db.Column(db.Boolean, default=True)

    # Current status
    status = db.Column(db.Enum(ServerStatus), default=ServerStatus.OFFLINE)
    last_ping = db.Column(db.DateTime, nullable=True)
    uptime_seconds = db.Column(db.Integer, default=0)

    # Relationships
    server = db.relationship("Server", backref="node")
    cluster = db.relationship("ServerCluster", backref="nodes")

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ServerDeployment(db.Model):
    """Track server deployments and updates."""

    __tablename__ = "server_deployments"

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey("server.id"), nullable=False)
    cluster_id = db.Column(
        db.Integer, db.ForeignKey("server_clusters.id"), nullable=True
    )

    # Deployment details
    deployment_type = db.Column(
        db.String(50), nullable=False
    )  # update, config, restart, etc.
    version = db.Column(db.String(50), nullable=True)
    status = db.Column(db.Enum(DeploymentStatus), default=DeploymentStatus.PENDING)

    # Deployment configuration
    config_data = db.Column(db.JSON, nullable=True)
    rollback_data = db.Column(db.JSON, nullable=True)

    # Timing
    scheduled_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Progress tracking
    total_steps = db.Column(db.Integer, default=1)
    completed_steps = db.Column(db.Integer, default=0)
    current_step = db.Column(db.String(200), nullable=True)

    # Results
    success = db.Column(db.Boolean, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    logs = db.Column(db.Text, nullable=True)

    # User tracking
    initiated_by = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class LoadBalancerRule(db.Model):
    """Load balancing rules for server clusters."""

    __tablename__ = "load_balancer_rules"

    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(
        db.Integer, db.ForeignKey("server_clusters.id"), nullable=False
    )

    name = db.Column(db.String(100), nullable=False)
    rule_type = db.Column(
        db.String(50), nullable=False
    )  # round_robin, least_connections, etc.
    priority = db.Column(db.Integer, default=100)

    # Rule configuration
    config = db.Column(db.JSON, nullable=True)
    conditions = db.Column(db.JSON, nullable=True)  # Conditions for rule application

    # Status
    enabled = db.Column(db.Boolean, default=True)

    cluster = db.relationship("ServerCluster", backref="lb_rules")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


@dataclass
class ServerHealth:
    """Server health check result."""

    server_id: int
    status: ServerStatus
    response_time_ms: float
    cpu_usage: float
    memory_usage: float
    player_count: int
    uptime: int
    last_check: datetime


@dataclass
class ClusterStats:
    """Cluster statistics."""

    total_servers: int
    online_servers: int
    total_players: int
    avg_cpu: float
    avg_memory: float
    avg_response_time: float


class ServerManager:
    """Manage individual servers remotely."""

    def __init__(self):
        self.ssh_connections = {}

    def get_ssh_connection(self, node: ServerNode):
        """Get or create SSH connection to server node."""
        key = f"{node.hostname}:{node.ssh_port}"

        if key not in self.ssh_connections:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # Use SSH key if provided, otherwise password auth
                if node.ssh_key_path:
                    ssh.connect(
                        hostname=node.hostname,
                        port=node.ssh_port,
                        username=node.ssh_username,
                        key_filename=node.ssh_key_path,
                        timeout=10,
                    )
                else:
                    # For development, you might use password auth
                    ssh.connect(
                        hostname=node.hostname,
                        port=node.ssh_port,
                        username=node.ssh_username,
                        timeout=10,
                    )

                self.ssh_connections[key] = ssh
            except Exception as e:
                # Connection failed; return None so caller can handle it
                print(f"Failed to connect to {node.hostname}: {e}")
                return None

        return self.ssh_connections[key]

    def execute_command(self, node: ServerNode, command: str) -> Tuple[bool, str, str]:
        """Execute command on remote server."""
        ssh = self.get_ssh_connection(node)
        if not ssh:
            return False, "", "Failed to establish SSH connection"

        try:
            stdin, stdout, stderr = ssh.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()

            stdout_data = stdout.read().decode("utf-8")
            stderr_data = stderr.read().decode("utf-8")

            return exit_code == 0, stdout_data, stderr_data
        except Exception as e:
            return False, "", str(e)

    def check_server_health(self, node: ServerNode) -> ServerHealth:
        """Check health of a server node."""
        start_time = time.time()

        # Basic ping test
        try:
            sock = socket.create_connection(
                (node.ip_address, node.server.port), timeout=5
            )
            sock.close()
            response_time = (time.time() - start_time) * 1000
            status = ServerStatus.ONLINE
        except Exception:
            response_time = 999999
            status = ServerStatus.OFFLINE

        # Get system metrics via SSH if online
        cpu_usage = 0.0
        memory_usage = 0.0
        uptime = 0

        if status == ServerStatus.ONLINE:
            try:
                # Get CPU usage
                success, cpu_out, _ = self.execute_command(
                    node, "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"
                )
                if success and cpu_out.strip():
                    cpu_usage = float(cpu_out.strip())

                # Get memory usage
                success, mem_out, _ = self.execute_command(
                    node, "free | grep Mem | awk '{printf \"%.1f\", $3/$2 * 100.0}'"
                )
                if success and mem_out.strip():
                    memory_usage = float(mem_out.strip())

                # Get uptime
                success, uptime_out, _ = self.execute_command(
                    node, "cat /proc/uptime | cut -d' ' -f1"
                )
                if success and uptime_out.strip():
                    uptime = int(float(uptime_out.strip()))

            except Exception as e:
                # Log and continue; metrics are best-effort
                print(f"Error getting metrics for {node.hostname}: {e}")

        # Get player count (would be implemented based on game server query)
        player_count = 0  # Placeholder

        return ServerHealth(
            server_id=node.server_id,
            status=status,
            response_time_ms=response_time,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            player_count=player_count,
            uptime=uptime,
            last_check=datetime.now(timezone.utc),
        )

    def start_server(self, node: ServerNode) -> bool:
        """Start a server."""
        node.status = ServerStatus.STARTING
        db.session.commit()

        # Implementation would depend on your server startup script
        success, stdout, stderr = self.execute_command(
            node, f"systemctl start etlegacy-{node.server.name}"
        )

        if success:
            node.status = ServerStatus.ONLINE
        else:
            node.status = ServerStatus.ERROR

        db.session.commit()
        return success

    def stop_server(self, node: ServerNode) -> bool:
        """Stop a server."""
        node.status = ServerStatus.STOPPING
        db.session.commit()

        success, stdout, stderr = self.execute_command(
            node, f"systemctl stop etlegacy-{node.server.name}"
        )

        if success:
            node.status = ServerStatus.OFFLINE
        else:
            node.status = ServerStatus.ERROR

        db.session.commit()
        return success

    def restart_server(self, node: ServerNode) -> bool:
        """Restart a server."""
        return self.stop_server(node) and self.start_server(node)


class ClusterManager:
    """Manage server clusters and orchestration."""

    def __init__(self):
        self.server_manager = ServerManager()

    def get_cluster_health(
        self, cluster_id: int
    ) -> Tuple[ClusterStats, List[ServerHealth]]:
        """Get comprehensive cluster health information."""
        cluster = db.session.query(ServerCluster).get(cluster_id)
        if not cluster:
            return None, []

        nodes = db.session.query(ServerNode).filter_by(cluster_id=cluster_id).all()
        health_checks = []

        total_cpu = 0
        total_memory = 0
        total_response_time = 0
        online_count = 0
        total_players = 0

        for node in nodes:
            health = self.server_manager.check_server_health(node)
            health_checks.append(health)

            if health.status == ServerStatus.ONLINE:
                online_count += 1
                total_cpu += health.cpu_usage
                total_memory += health.memory_usage
                total_response_time += health.response_time_ms
                total_players += health.player_count

        # Calculate averages
        avg_cpu = total_cpu / online_count if online_count > 0 else 0
        avg_memory = total_memory / online_count if online_count > 0 else 0
        avg_response_time = (
            total_response_time / online_count if online_count > 0 else 0
        )

        stats = ClusterStats(
            total_servers=len(nodes),
            online_servers=online_count,
            total_players=total_players,
            avg_cpu=avg_cpu,
            avg_memory=avg_memory,
            avg_response_time=avg_response_time,
        )

        return stats, health_checks

    def auto_scale_cluster(self, cluster_id: int):
        """Automatically scale cluster based on load."""
        cluster = db.session.query(ServerCluster).get(cluster_id)
        if not cluster or not cluster.auto_scaling_enabled:
            return

        stats, health_checks = self.get_cluster_health(cluster_id)

        # Scale up if CPU usage is high
        if (
            stats.avg_cpu > cluster.target_cpu_utilization
            and stats.online_servers < cluster.max_servers
        ):
            self._scale_up_cluster(cluster)

        # Scale down if CPU usage is low and we have more than minimum servers
        elif (
            stats.avg_cpu < (cluster.target_cpu_utilization * 0.5)
            and stats.online_servers > cluster.min_servers
        ):
            self._scale_down_cluster(cluster)

    def _scale_up_cluster(self, cluster: ServerCluster):
        """Add a server to the cluster."""
        # Find an offline node to bring online
        offline_node = (
            db.session.query(ServerNode)
            .filter_by(cluster_id=cluster.id, status=ServerStatus.OFFLINE)
            .first()
        )

        if offline_node:
            self.server_manager.start_server(offline_node)

    def _scale_down_cluster(self, cluster: ServerCluster):
        """Remove a server from the cluster."""
        # Find a node with low load to take offline
        # This would need more sophisticated logic in production
        online_nodes = (
            db.session.query(ServerNode)
            .filter_by(cluster_id=cluster.id, status=ServerStatus.ONLINE)
            .all()
        )

        if len(online_nodes) > cluster.min_servers:
            # Take the least loaded server offline
            # For now, just take the first one
            self.server_manager.stop_server(online_nodes[0])


class DeploymentManager:
    """Manage deployments across servers and clusters."""

    def __init__(self):
        self.server_manager = ServerManager()

    def create_deployment(
        self, server_ids: List[int], deployment_type: str, config: dict
    ) -> int:
        """Create a new deployment."""
        deployment = ServerDeployment(
            deployment_type=deployment_type,
            config_data=config,
            initiated_by=(
                current_user.email
                if current_user and current_user.is_authenticated
                else "system"
            ),
            total_steps=len(server_ids) * 3,  # stop, update, start
        )

        db.session.add(deployment)
        db.session.commit()

        # Start deployment in background thread
        thread = threading.Thread(
            target=self._execute_deployment,
            args=(deployment.id, server_ids),
            daemon=True,
        )
        thread.start()

        return deployment.id

    def _execute_deployment(self, deployment_id: int, server_ids: List[int]):
        """Execute deployment across servers."""
        deployment = db.session.query(ServerDeployment).get(deployment_id)
        if not deployment:
            return

        deployment.status = DeploymentStatus.IN_PROGRESS
        deployment.started_at = datetime.now(timezone.utc)
        db.session.commit()

        try:
            for server_id in server_ids:
                node = (
                    db.session.query(ServerNode).filter_by(server_id=server_id).first()
                )
                if not node:
                    continue

                # Stop server
                deployment.current_step = f"Stopping server {node.server.name}"
                db.session.commit()

                self.server_manager.stop_server(node)
                deployment.completed_steps += 1
                db.session.commit()

                # Update/configure server
                deployment.current_step = f"Updating server {node.server.name}"
                db.session.commit()

                # Actual update logic would go here
                time.sleep(2)  # Simulate update time

                deployment.completed_steps += 1
                db.session.commit()

                # Start server
                deployment.current_step = f"Starting server {node.server.name}"
                db.session.commit()

                self.server_manager.start_server(node)
                deployment.completed_steps += 1
                db.session.commit()

            deployment.status = DeploymentStatus.COMPLETED
            deployment.success = True
            deployment.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.success = False
            deployment.error_message = str(e)
            deployment.completed_at = datetime.now(timezone.utc)

        db.session.commit()


# Global managers
cluster_manager = ClusterManager()
deployment_manager = DeploymentManager()


# Routes for multi-server management
@multi_server_bp.route("/admin/servers/clusters")
@login_required
def cluster_dashboard():
    """Multi-server cluster management dashboard."""
    if not current_user.is_system_admin:
        return redirect(url_for("dashboard"))

    clusters = db.session.query(ServerCluster).all()
    cluster_data = []

    for cluster in clusters:
        stats, health_checks = cluster_manager.get_cluster_health(cluster.id)
        cluster_data.append(
            {"cluster": cluster, "stats": stats, "health": health_checks}
        )

    # Get recent deployments
    recent_deployments = (
        db.session.query(ServerDeployment)
        .order_by(desc(ServerDeployment.created_at))
        .limit(10)
        .all()
    )

    return render_template(
        "admin_multi_server.html",
        cluster_data=cluster_data,
        recent_deployments=recent_deployments,
    )


@multi_server_bp.route("/admin/servers/cluster/<int:cluster_id>")
@login_required
def cluster_detail(cluster_id):
    """Detailed cluster management view."""
    if not current_user.is_system_admin:
        return redirect(url_for("dashboard"))

    cluster = db.session.query(ServerCluster).get_or_404(cluster_id)
    stats, health_checks = cluster_manager.get_cluster_health(cluster_id)

    # Get cluster nodes
    nodes = db.session.query(ServerNode).filter_by(cluster_id=cluster_id).all()

    # Get recent deployments for this cluster
    deployments = (
        db.session.query(ServerDeployment)
        .filter_by(cluster_id=cluster_id)
        .order_by(desc(ServerDeployment.created_at))
        .limit(20)
        .all()
    )

    return render_template(
        "cluster_detail.html",
        cluster=cluster,
        stats=stats,
        health_checks=health_checks,
        nodes=nodes,
        deployments=deployments,
    )


def start_multi_server_system(app=None):
    """Start the multi-server management system."""

    if app is None:
        print("Warning: Multi-server system requires Flask app context")
        return

    # Start background monitoring and auto-scaling
    def monitoring_loop():
        with app.app_context():
            while True:
                try:
                    clusters = db.session.query(ServerCluster).all()
                    for cluster in clusters:
                        cluster_manager.auto_scale_cluster(cluster.id)
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    print(f"Multi-server monitoring error: {e}")
                    time.sleep(30)

    thread = threading.Thread(target=monitoring_loop, daemon=True)
    thread.start()
    print("✓ Multi-server management system started")
