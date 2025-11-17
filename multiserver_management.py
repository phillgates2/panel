"""
Multi-Server Management Hub

Centralized management system for multiple ET:Legacy servers with cluster operations,
load balancing, synchronized deployments, and cross-server player management.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from datetime import datetime, timezone, timedelta
import json
import threading
import subprocess
from collections import defaultdict


multiserver_bp = Blueprint('multiserver', __name__)


class ServerCluster(db.Model):
    """Define server clusters for grouped management."""
    __tablename__ = 'server_cluster'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    region = db.Column(db.String(64), nullable=True)  # US-East, EU-West, etc.
    
    # Cluster configuration
    auto_failover = db.Column(db.Boolean, default=False)
    load_balancing = db.Column(db.Boolean, default=False)
    shared_config = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    creator = db.relationship('User')


class ClusterServer(db.Model):
    """Association between servers and clusters."""
    __tablename__ = 'cluster_server'
    
    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('server_cluster.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    
    # Server role in cluster
    role = db.Column(db.String(32), default='member')  # primary, backup, member, load_balancer
    priority = db.Column(db.Integer, default=100)  # For failover ordering
    weight = db.Column(db.Integer, default=100)  # For load balancing
    
    is_active = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    cluster = db.relationship('ServerCluster', backref=db.backref('servers', lazy='dynamic'))
    server = db.relationship('Server')


class CrossServerPlayer(db.Model):
    """Global player identity across multiple servers."""
    __tablename__ = 'cross_server_player'
    
    id = db.Column(db.Integer, primary_key=True)
    player_name = db.Column(db.String(128), nullable=False)
    player_guid = db.Column(db.String(64), nullable=False, unique=True)
    
    # Global player stats
    total_playtime_minutes = db.Column(db.Integer, default=0)
    total_kills = db.Column(db.Integer, default=0)
    total_deaths = db.Column(db.Integer, default=0)
    total_sessions = db.Column(db.Integer, default=0)
    
    # Player status
    is_banned = db.Column(db.Boolean, default=False)
    is_vip = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, nullable=True)
    last_server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=True)
    
    # Registration
    first_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    last_server = db.relationship('Server', foreign_keys=[last_server_id])


class ServerSync(db.Model):
    """Track synchronization operations between servers."""
    __tablename__ = 'server_sync'
    
    id = db.Column(db.Integer, primary_key=True)
    sync_type = db.Column(db.String(64), nullable=False)  # config, bans, maps, etc.
    source_server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=True)
    target_servers = db.Column(db.Text, nullable=False)  # JSON array of server IDs
    
    status = db.Column(db.String(32), default='pending')  # pending, running, completed, failed
    progress = db.Column(db.Integer, default=0)  # Percentage complete
    
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    initiated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Results
    sync_log = db.Column(db.Text, nullable=True)
    success_count = db.Column(db.Integer, default=0)
    failure_count = db.Column(db.Integer, default=0)
    
    source_server = db.relationship('Server', foreign_keys=[source_server_id])
    initiator = db.relationship('User')


class LoadBalancer(db.Model):
    """Load balancer configuration for server clusters."""
    __tablename__ = 'load_balancer'
    
    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('server_cluster.id'), nullable=False)
    
    algorithm = db.Column(db.String(32), default='round_robin')  # round_robin, least_players, weighted
    redirect_full_servers = db.Column(db.Boolean, default=True)
    max_player_difference = db.Column(db.Integer, default=5)  # For load balancing
    
    # Health check settings
    health_check_interval = db.Column(db.Integer, default=30)  # seconds
    health_check_timeout = db.Column(db.Integer, default=5)   # seconds
    failure_threshold = db.Column(db.Integer, default=3)      # consecutive failures before removing
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    cluster = db.relationship('ServerCluster', backref=db.backref('load_balancer', uselist=False))


class MultiServerManager:
    """Centralized manager for multi-server operations."""
    
    def __init__(self):
        self.active_syncs = {}  # Track running sync operations
        self.load_balancer_state = defaultdict(dict)  # Track server states for load balancing
    
    def create_cluster(self, name, description, region, auto_failover=False, 
                      load_balancing=False, shared_config=True, user_id=None):
        """Create a new server cluster."""
        try:
            cluster = ServerCluster(
                name=name,
                description=description,
                region=region,
                auto_failover=auto_failover,
                load_balancing=load_balancing,
                shared_config=shared_config,
                created_by=user_id
            )
            
            db.session.add(cluster)
            db.session.commit()
            
            return cluster
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    def add_server_to_cluster(self, cluster_id, server_id, role='member', 
                             priority=100, weight=100):
        """Add a server to a cluster."""
        try:
            # Check if server is already in any cluster
            existing = ClusterServer.query.filter_by(server_id=server_id).first()
            if existing:
                raise ValueError(f"Server already belongs to cluster: {existing.cluster.name}")
            
            cluster_server = ClusterServer(
                cluster_id=cluster_id,
                server_id=server_id,
                role=role,
                priority=priority,
                weight=weight
            )
            
            db.session.add(cluster_server)
            db.session.commit()
            
            return cluster_server
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    def sync_configuration(self, source_server_id, target_server_ids, 
                          sync_type='config', user_id=None):
        """Synchronize configuration between servers."""
        try:
            sync_record = ServerSync(
                sync_type=sync_type,
                source_server_id=source_server_id,
                target_servers=json.dumps(target_server_ids),
                initiated_by=user_id,
                status='pending'
            )
            
            db.session.add(sync_record)
            db.session.commit()
            
            # Start sync in background thread
            sync_thread = threading.Thread(
                target=self._execute_sync,
                args=(sync_record.id,),
                daemon=True
            )
            sync_thread.start()
            
            return sync_record
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    def _execute_sync(self, sync_id):
        """Execute a synchronization operation in background."""
        sync_record = ServerSync.query.get(sync_id)
        if not sync_record:
            return
        
        try:
            sync_record.status = 'running'
            db.session.commit()
            
            from app import Server
            source_server = sync_record.source_server
            target_server_ids = json.loads(sync_record.target_servers)
            target_servers = Server.query.filter(Server.id.in_(target_server_ids)).all()
            
            sync_log = []
            success_count = 0
            failure_count = 0
            total_targets = len(target_servers)
            
            for i, target_server in enumerate(target_servers):
                try:
                    if sync_record.sync_type == 'config':
                        self._sync_server_config(source_server, target_server)
                    elif sync_record.sync_type == 'bans':
                        self._sync_server_bans(source_server, target_server)
                    elif sync_record.sync_type == 'maps':
                        self._sync_server_maps(source_server, target_server)
                    
                    success_count += 1
                    sync_log.append(f"✓ {target_server.name}: Sync successful")
                    
                except Exception as e:
                    failure_count += 1
                    sync_log.append(f"✗ {target_server.name}: {str(e)}")
                
                # Update progress
                progress = int(((i + 1) / total_targets) * 100)
                sync_record.progress = progress
                db.session.commit()
            
            # Complete sync
            sync_record.status = 'completed' if failure_count == 0 else 'failed'
            sync_record.completed_at = datetime.now(timezone.utc)
            sync_record.success_count = success_count
            sync_record.failure_count = failure_count
            sync_record.sync_log = '\n'.join(sync_log)
            db.session.commit()
            
        except Exception as e:
            sync_record.status = 'failed'
            sync_record.sync_log = f"Sync failed: {str(e)}"
            db.session.commit()
    
    def _sync_server_config(self, source_server, target_server):
        """Synchronize configuration from source to target server."""
        from config_manager import ConfigManager
        
        # Get current active config from source
        source_manager = ConfigManager(source_server.id)
        source_config = source_manager.get_current_config()
        
        if not source_config:
            raise Exception("No active configuration on source server")
        
        # Create new version on target with source config
        target_manager = ConfigManager(target_server.id)
        config_data = json.loads(source_config.config_data)
        
        # Create and deploy the configuration
        new_version = target_manager.create_version(
            config_data=config_data,
            user_id=1,  # System user
            change_summary=f"Synced from {source_server.name}"
        )
        
        deployment = target_manager.deploy_version(new_version.id, user_id=1)
        
        if deployment.deployment_status != 'success':
            raise Exception(f"Deployment failed: {deployment.deployment_log}")
    
    def _sync_server_bans(self, source_server, target_server):
        """Synchronize ban lists between servers."""
        # This would integrate with your ban management system
        # For now, this is a placeholder
        print(f"Syncing bans from {source_server.name} to {target_server.name}")
    
    def _sync_server_maps(self, source_server, target_server):
        """Synchronize map files between servers."""
        # This would handle map file synchronization
        # For now, this is a placeholder  
        print(f"Syncing maps from {source_server.name} to {target_server.name}")
    
    def get_cluster_status(self, cluster_id):
        """Get comprehensive status of a server cluster."""
        cluster = ServerCluster.query.get(cluster_id)
        if not cluster:
            return None
        
        servers_data = []
        total_players = 0
        online_servers = 0
        
        from monitoring_system import ServerMetrics
        
        for cluster_server in cluster.servers:
            server = cluster_server.server
            
            # Get latest metrics
            latest_metric = ServerMetrics.query.filter_by(
                server_id=server.id
            ).order_by(ServerMetrics.timestamp.desc()).first()
            
            server_info = {
                'server': server,
                'cluster_role': cluster_server.role,
                'priority': cluster_server.priority,
                'weight': cluster_server.weight,
                'is_active': cluster_server.is_active,
                'metrics': latest_metric
            }
            
            if latest_metric:
                if latest_metric.is_online:
                    online_servers += 1
                if latest_metric.player_count:
                    total_players += latest_metric.player_count
            
            servers_data.append(server_info)
        
        return {
            'cluster': cluster,
            'servers': servers_data,
            'total_players': total_players,
            'online_servers': online_servers,
            'total_servers': len(servers_data)
        }
    
    def balance_players(self, cluster_id):
        """Perform load balancing for a cluster."""
        cluster_status = self.get_cluster_status(cluster_id)
        if not cluster_status:
            return False
        
        # Simple load balancing logic
        servers = cluster_status['servers']
        online_servers = [s for s in servers if s['metrics'] and s['metrics'].is_online]
        
        if len(online_servers) < 2:
            return False  # Need at least 2 servers for balancing
        
        # Calculate average players per server
        total_players = sum(s['metrics'].player_count or 0 for s in online_servers)
        target_per_server = total_players // len(online_servers)
        
        # Find servers that need rebalancing
        overloaded = [s for s in online_servers 
                     if (s['metrics'].player_count or 0) > target_per_server + 3]
        underloaded = [s for s in online_servers 
                      if (s['metrics'].player_count or 0) < target_per_server - 3]
        
        # Implement player redirection logic here
        # This would involve RCON commands to redirect players
        
        return True
    
    def get_cross_server_player_stats(self, limit=100):
        """Get global player statistics across all servers."""
        return CrossServerPlayer.query.order_by(
            CrossServerPlayer.total_playtime_minutes.desc()
        ).limit(limit).all()
    
    def update_player_session(self, server_id, player_name, player_guid, 
                             session_data):
        """Update cross-server player session data."""
        try:
            # Update or create cross-server player record
            player = CrossServerPlayer.query.filter_by(player_guid=player_guid).first()
            
            if not player:
                player = CrossServerPlayer(
                    player_name=player_name,
                    player_guid=player_guid,
                    last_server_id=server_id
                )
                db.session.add(player)
            else:
                player.player_name = player_name  # Update in case of name change
                player.last_server_id = server_id
            
            # Update stats
            player.last_seen = datetime.now(timezone.utc)
            player.total_sessions += 1
            
            if 'playtime' in session_data:
                player.total_playtime_minutes += session_data['playtime']
            if 'kills' in session_data:
                player.total_kills += session_data['kills']
            if 'deaths' in session_data:
                player.total_deaths += session_data['deaths']
            
            db.session.commit()
            
            return player
            
        except Exception as e:
            db.session.rollback()
            raise e


# Global multi-server manager instance
multiserver_manager = MultiServerManager()


@multiserver_bp.route('/admin/multiserver/clusters')
@login_required
def cluster_management():
    """Cluster management dashboard."""
    if not current_user.is_system_admin:
        return redirect(url_for('dashboard'))
    
    clusters = ServerCluster.query.order_by(ServerCluster.created_at.desc()).all()
    
    cluster_stats = []
    for cluster in clusters:
        status = multiserver_manager.get_cluster_status(cluster.id)
        cluster_stats.append(status)
    
    return render_template('admin_multiserver_clusters.html', 
                         cluster_stats=cluster_stats)


@multiserver_bp.route('/admin/multiserver/clusters/create', methods=['POST'])
@login_required
def create_cluster():
    """Create a new server cluster."""
    if not current_user.is_system_admin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        
        cluster = multiserver_manager.create_cluster(
            name=data['name'],
            description=data.get('description', ''),
            region=data.get('region', ''),
            auto_failover=data.get('auto_failover', False),
            load_balancing=data.get('load_balancing', False),
            shared_config=data.get('shared_config', True),
            user_id=current_user.id
        )
        
        return jsonify({
            'success': True,
            'cluster_id': cluster.id,
            'message': 'Cluster created successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@multiserver_bp.route('/admin/multiserver/sync', methods=['POST'])
@login_required
def sync_servers():
    """Synchronize configuration between servers."""
    if not current_user.is_system_admin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        
        sync_record = multiserver_manager.sync_configuration(
            source_server_id=data['source_server_id'],
            target_server_ids=data['target_server_ids'],
            sync_type=data.get('sync_type', 'config'),
            user_id=current_user.id
        )
        
        return jsonify({
            'success': True,
            'sync_id': sync_record.id,
            'message': 'Synchronization started'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@multiserver_bp.route('/admin/multiserver/players')
@login_required
def cross_server_players():
    """Cross-server player management."""
    if not current_user.is_system_admin:
        return redirect(url_for('dashboard'))
    
    players = multiserver_manager.get_cross_server_player_stats(100)
    
    return render_template('admin_multiserver_players.html', players=players)


@multiserver_bp.route('/api/multiserver/cluster/<int:cluster_id>/balance', 
                     methods=['POST'])
@login_required
def balance_cluster(cluster_id):
    """Trigger load balancing for a cluster."""
    if not current_user.is_system_admin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        result = multiserver_manager.balance_players(cluster_id)
        
        return jsonify({
            'success': result,
            'message': 'Load balancing completed' if result else 'Load balancing failed'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500