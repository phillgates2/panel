"""
Configuration Management Routes

Web interface for managing server configurations, templates, and deployments.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from config_manager import ConfigTemplate, ConfigVersion, ConfigDeployment, ConfigManager
import json
from datetime import datetime, timezone


config_bp = Blueprint('config', __name__)


@config_bp.route('/admin/config/templates')
@login_required
def config_templates():
    """Manage configuration templates."""
    if not current_user.is_system_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    templates = ConfigTemplate.query.order_by(ConfigTemplate.created_at.desc()).all()
    return render_template('admin_config_templates.html', templates=templates)


@config_bp.route('/admin/config/templates/create', methods=['GET', 'POST'])
@login_required
def create_template():
    """Create a new configuration template."""
    if not current_user.is_system_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            template = ConfigTemplate(
                name=data['name'],
                description=data.get('description', ''),
                game_type=data['game_type'],
                template_data=json.dumps(data['template_data']),
                created_by=current_user.id
            )
            
            db.session.add(template)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Configuration template created successfully',
                'template_id': template.id
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error creating template: {str(e)}'
            }), 500
    
    return render_template('admin_config_template_create.html')


@config_bp.route('/admin/config/templates/<int:template_id>')
@login_required
def edit_template(template_id):
    """Edit a configuration template."""
    if not current_user.is_system_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    template = ConfigTemplate.query.get_or_404(template_id)
    template_data = json.loads(template.template_data)
    
    return render_template('admin_config_template_edit.html', 
                         template=template, 
                         template_data=template_data)


@config_bp.route('/admin/config/templates/<int:template_id>/update', methods=['POST'])
@login_required
def update_template(template_id):
    """Update a configuration template."""
    if not current_user.is_system_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        template = ConfigTemplate.query.get_or_404(template_id)
        data = request.get_json()
        
        template.name = data['name']
        template.description = data.get('description', '')
        template.game_type = data['game_type']
        template.template_data = json.dumps(data['template_data'])
        template.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Template updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating template: {str(e)}'
        }), 500


@config_bp.route('/server/<int:server_id>/config')
@login_required
def server_config(server_id):
    """Manage server configuration."""
    from app import Server
    
    server = Server.query.get_or_404(server_id)
    
    # Check permissions
    if not (current_user.is_system_admin or server.owner_id == current_user.id):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    config_manager = ConfigManager(server_id)
    current_config = config_manager.get_current_config()
    version_history = config_manager.get_version_history(20)
    templates = ConfigTemplate.query.filter_by(game_type=server.game_type).all()
    
    return render_template('server_config.html', 
                         server=server,
                         current_config=current_config,
                         version_history=version_history,
                         templates=templates)


@config_bp.route('/server/<int:server_id>/config/create', methods=['POST'])
@login_required
def create_config_version(server_id):
    """Create a new configuration version."""
    from app import Server
    
    server = Server.query.get_or_404(server_id)
    
    # Check permissions
    if not (current_user.is_system_admin or server.owner_id == current_user.id):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        config_manager = ConfigManager(server_id)
        
        # Validate configuration
        validation = config_manager.validate_config(data['config_data'])
        if validation['errors']:
            return jsonify({
                'success': False,
                'message': 'Configuration validation failed',
                'errors': validation['errors'],
                'warnings': validation['warnings']
            }), 400
        
        version = config_manager.create_version(
            config_data=data['config_data'],
            user_id=current_user.id,
            change_summary=data.get('change_summary', '')
        )
        
        return jsonify({
            'success': True,
            'message': 'Configuration version created successfully',
            'version_id': version.id,
            'version_number': version.version_number,
            'warnings': validation['warnings']
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating configuration version: {str(e)}'
        }), 500


@config_bp.route('/server/<int:server_id>/config/<int:version_id>/deploy', methods=['POST'])
@login_required
def deploy_config_version(server_id, version_id):
    """Deploy a configuration version."""
    from app import Server
    
    server = Server.query.get_or_404(server_id)
    
    # Check permissions
    if not (current_user.is_system_admin or server.owner_id == current_user.id):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        config_manager = ConfigManager(server_id)
        deployment = config_manager.deploy_version(version_id, current_user.id)
        
        return jsonify({
            'success': deployment.deployment_status == 'success',
            'message': deployment.deployment_log,
            'deployment_id': deployment.id,
            'status': deployment.deployment_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deploying configuration: {str(e)}'
        }), 500


@config_bp.route('/server/<int:server_id>/config/<int:version_id>/rollback', methods=['POST'])
@login_required
def rollback_config_version(server_id, version_id):
    """Rollback to a previous configuration version."""
    from app import Server
    
    server = Server.query.get_or_404(server_id)
    
    # Check permissions
    if not (current_user.is_system_admin or server.owner_id == current_user.id):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        config_manager = ConfigManager(server_id)
        deployment = config_manager.rollback_to_version(version_id, current_user.id)
        
        return jsonify({
            'success': deployment.deployment_status == 'success',
            'message': deployment.deployment_log,
            'deployment_id': deployment.id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error rolling back configuration: {str(e)}'
        }), 500


@config_bp.route('/server/<int:server_id>/config/compare')
@login_required
def compare_config_versions(server_id):
    """Compare two configuration versions."""
    from app import Server
    
    server = Server.query.get_or_404(server_id)
    
    # Check permissions
    if not (current_user.is_system_admin or server.owner_id == current_user.id):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    version1_id = request.args.get('v1', type=int)
    version2_id = request.args.get('v2', type=int)
    
    if not version1_id or not version2_id:
        return jsonify({
            'success': False,
            'message': 'Both version IDs are required'
        }), 400
    
    try:
        config_manager = ConfigManager(server_id)
        differences = config_manager.compare_versions(version1_id, version2_id)
        
        return jsonify({
            'success': True,
            'differences': differences
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error comparing versions: {str(e)}'
        }), 500


@config_bp.route('/server/<int:server_id>/config/<int:version_id>/details')
@login_required
def config_version_details(server_id, version_id):
    """Get detailed information about a configuration version."""
    from app import Server
    
    server = Server.query.get_or_404(server_id)
    
    # Check permissions
    if not (current_user.is_system_admin or server.owner_id == current_user.id):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    version = ConfigVersion.query.filter_by(
        server_id=server_id,
        id=version_id
    ).first_or_404()
    
    deployments = ConfigDeployment.query.filter_by(
        config_version_id=version_id
    ).order_by(ConfigDeployment.started_at.desc()).all()
    
    return jsonify({
        'success': True,
        'version': {
            'id': version.id,
            'version_number': version.version_number,
            'config_data': json.loads(version.config_data),
            'config_hash': version.config_hash,
            'change_summary': version.change_summary,
            'created_at': version.created_at.isoformat(),
            'is_active': version.is_active,
            'creator': version.creator.email if version.creator else 'Unknown'
        },
        'deployments': [{
            'id': d.id,
            'status': d.deployment_status,
            'log': d.deployment_log,
            'started_at': d.started_at.isoformat(),
            'completed_at': d.completed_at.isoformat() if d.completed_at else None,
            'deployer': d.deployer.email if d.deployer else 'Unknown'
        } for d in deployments]
    })


@config_bp.route('/api/config/templates/<int:template_id>/data')
@login_required
def get_template_data(template_id):
    """Get template data for creating new configuration."""
    template = ConfigTemplate.query.get_or_404(template_id)
    
    return jsonify({
        'success': True,
        'template_data': json.loads(template.template_data)
    })


@config_bp.route('/admin/config/deployments')
@login_required
def deployment_history():
    """View deployment history across all servers."""
    if not current_user.is_system_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    deployments = db.session.query(ConfigDeployment)\
        .join(ConfigVersion)\
        .order_by(ConfigDeployment.started_at.desc())\
        .limit(100).all()
    
    return render_template('admin_config_deployments.html', deployments=deployments)