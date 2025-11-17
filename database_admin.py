"""
Database Admin Integration for Panel
Provides embedded database management interface for SQLite and PostgreSQL
Replaces legacy phpMyAdmin with modern Python-based admin UI
"""

import os
import subprocess
import tempfile
import shutil
from flask import render_template_string, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
import sqlite3

try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class DatabaseAdmin:
    """Embedded database admin functionality for Panel (SQLite & PostgreSQL)"""
    
    def __init__(self, app, db):
        self.app = app
        self.db = db
        
    def is_postgres(self):
        """Check if using PostgreSQL"""
        return POSTGRES_AVAILABLE and os.environ.get('PANEL_USE_SQLITE', '1') != '1'
        
    def get_db_connection(self):
        """Get database connection based on configuration"""
        if self.is_postgres():
            return psycopg2.connect(
                host=os.environ.get('PANEL_DB_HOST', 'localhost'),
                port=int(os.environ.get('PANEL_DB_PORT', '5432')),
                user=os.environ.get('PANEL_DB_USER', 'paneluser'),
                password=os.environ.get('PANEL_DB_PASS', ''),
                database=os.environ.get('PANEL_DB_NAME', 'paneldb'),
                cursor_factory=psycopg2.extras.RealDictCursor
            )
        else:
            db_path = os.path.join(self.app.instance_path, 'panel.db')
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # Dict-like access
            return conn
    
    def execute_query(self, query, params=None):
        """Execute a database query safely"""
        try:
            conn = self.get_db_connection()
            if self.is_postgres():
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    if query.strip().upper().startswith('SELECT') or query.strip().upper().startswith('SHOW'):
                        results = cursor.fetchall()
                        conn.close()
                        return {'success': True, 'data': results}
                    else:
                        conn.commit()
                        conn.close()
                        return {'success': True, 'message': f'Query executed successfully. {cursor.rowcount} rows affected.'}
            else:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                if query.strip().upper().startswith('SELECT') or query.strip().upper().startswith('PRAGMA'):
                    results = [dict(row) for row in cursor.fetchall()]
                    conn.close()
                    return {'success': True, 'data': results}
                else:
                    conn.commit()
                    conn.close()
                    return {'success': True, 'message': f'Query executed successfully. {cursor.rowcount} rows affected.'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_tables(self):
        """Get list of tables in the database"""
        if self.is_postgres():
            result = self.execute_query("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            if result['success']:
                return [row['tablename'] for row in result['data']]
        else:
            result = self.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
            if result['success']:
                return [row['name'] for row in result['data']]
        return []
    
    def get_table_structure(self, table_name):
        """Get table structure"""
        if self.is_postgres():
            query = """SELECT column_name, data_type, is_nullable, column_default 
                       FROM information_schema.columns 
                       WHERE table_name = %s AND table_schema = 'public'"""
            return self.execute_query(query, (table_name,))
        else:
            return self.execute_query(f"PRAGMA table_info(`{table_name}`)")
    
    def get_table_data(self, table_name, limit=100, offset=0):
        """Get table data with pagination"""
        query = f"SELECT * FROM `{table_name}` LIMIT {limit} OFFSET {offset}"
        return self.execute_query(query)
    
    def get_database_info(self):
        """Get database information"""
        info = {
            'type': 'PostgreSQL' if self.is_postgres() else 'SQLite',
            'tables': self.get_tables()
        }
        
        if self.is_postgres():
            result = self.execute_query("SELECT version()")
            if result['success'] and result['data']:
                info['version'] = result['data'][0]['version']
        
        result = self.execute_query("SELECT sqlite_version() as version")
        if result['success'] and result['data']:
            info['version'] = result['data'][0]['version']
        info['database'] = 'panel.db'
        
        return info


# HTML Templates for phpMyAdmin interface
DATABASE_ADMIN_BASE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Panel Database Manager</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8f9fa; }
        .header { background: #2c3e50; color: white; padding: 1rem; border-bottom: 2px solid #34495e; }
        .header h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
        .header .breadcrumb { font-size: 0.9rem; opacity: 0.8; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .sidebar { background: white; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .sidebar h2 { color: #2c3e50; margin-bottom: 1rem; font-size: 1.2rem; }
        .db-info { background: #ecf0f1; padding: 1rem; border-radius: 6px; margin-bottom: 1rem; }
        .db-info strong { color: #2c3e50; }
        .tables-list { list-style: none; }
        .tables-list li { margin: 0.5rem 0; }
        .tables-list a { color: #3498db; text-decoration: none; padding: 0.5rem; display: block; border-radius: 4px; transition: background 0.2s; }
        .tables-list a:hover, .tables-list a.active { background: #3498db; color: white; }
        .main-content { background: white; border-radius: 8px; padding: 2rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .btn { background: #3498db; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 1rem; margin-bottom: 1rem; transition: background 0.2s; }
        .btn:hover { background: #2980b9; }
        .btn-danger { background: #e74c3c; }
        .btn-danger:hover { background: #c0392b; }
        .btn-success { background: #27ae60; }
        .btn-success:hover { background: #229954; }
        table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #ecf0f1; }
        th { background: #f8f9fa; font-weight: 600; color: #2c3e50; }
        tr:hover { background: #f8f9fa; }
        .query-box { width: 100%; height: 200px; font-family: 'Courier New', monospace; padding: 1rem; border: 1px solid #ddd; border-radius: 4px; margin: 1rem 0; resize: vertical; }
        .alert { padding: 1rem; margin: 1rem 0; border-radius: 4px; }
        .alert-success { background: #d5edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-danger { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .pagination { margin: 1rem 0; }
        .pagination a, .pagination span { padding: 0.5rem 1rem; margin: 0 0.25rem; text-decoration: none; color: #3498db; border: 1px solid #ddd; border-radius: 4px; }
        .pagination .current { background: #3498db; color: white; }
        .nav-links { margin-bottom: 2rem; }
        .nav-links a { color: #3498db; text-decoration: none; margin-right: 1rem; }
        .nav-links a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🗄️ Panel Database Manager</h1>
        <div class="breadcrumb">{{ breadcrumb|safe }}</div>
    </div>
    <div class="container">
        <div class="nav-links">
            <a href="{{ url_for('admin_db_home') }}">🏠 Home</a>
            <a href="{{ url_for('admin_db_query') }}">🔍 SQL Query</a>
            <a href="{{ url_for('admin_db_export') }}">📤 Export</a>
            <a href="{{ url_for('admin_db_import') }}">📥 Import</a>
        </div>
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

DATABASE_ADMIN_HOME_TEMPLATE = '''
{% extends "database_admin_base.html" %}
{% block content %}
<div class="sidebar">
    <h2>Database Information</h2>
    <div class="db-info">
        <p><strong>Type:</strong> {{ db_info.type }}</p>
        <p><strong>Database:</strong> {{ db_info.database }}</p>
        {% if db_info.version %}<p><strong>Version:</strong> {{ db_info.version }}</p>{% endif %}
        <p><strong>Tables:</strong> {{ db_info.tables|length }}</p>
    </div>
    
    <h2>Tables</h2>
    <ul class="tables-list">
        {% for table in db_info.tables %}
        <li><a href="{{ url_for('admin_db_table', table_name=table) }}">📋 {{ table }}</a></li>
        {% endfor %}
    </ul>
</div>

<div class="main-content">
    <h2>Welcome to Panel Database Manager</h2>
    <p>This integrated database management interface allows you to:</p>
    <ul style="margin: 1rem 0; padding-left: 2rem;">
        <li>Browse and edit database tables</li>
        <li>Execute custom SQL queries</li>
        <li>Export and import data</li>
        <li>View database structure</li>
    </ul>
    
    <h3>Quick Actions</h3>
    <a href="{{ url_for('admin_db_query') }}" class="btn">Execute SQL Query</a>
    <a href="{{ url_for('admin_db_export') }}" class="btn btn-success">Export Database</a>
</div>
{% endblock %}
'''

DATABASE_ADMIN_TABLE_TEMPLATE = '''
{% extends "database_admin_base.html" %}
{% block content %}
<div class="sidebar">
    <h2>Table: {{ table_name }}</h2>
    <a href="{{ url_for('admin_db_table_structure', table_name=table_name) }}" class="btn">View Structure</a>
    <a href="{{ url_for('admin_db_query') }}?query=SELECT * FROM {{ table_name }}" class="btn">Query Table</a>
</div>

<div class="main-content">
    <h2>Table Data: {{ table_name }}</h2>
    
    {% if result.success %}
        {% if result.data %}
        <div class="pagination">
            Showing {{ offset + 1 }} to {{ offset + result.data|length }} of {{ total }} rows
        </div>
        
        <table>
            <thead>
                <tr>
                    {% for column in result.data[0].keys() %}
                    <th>{{ column }}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for row in result.data %}
                <tr>
                    {% for value in row.values() %}
                    <td>{{ value if value is not none else '<em>NULL</em>' }}</td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <div class="pagination">
            {% if offset > 0 %}
            <a href="{{ url_for('admin_db_table', table_name=table_name, offset=offset-limit) }}">&laquo; Previous</a>
            {% endif %}
            {% if result.data|length == limit %}
            <a href="{{ url_for('admin_db_table', table_name=table_name, offset=offset+limit) }}">Next &raquo;</a>
            {% endif %}
        </div>
        {% else %}
        <p>No data found in this table.</p>
        {% endif %}
    {% else %}
        <div class="alert alert-danger">Error: {{ result.error }}</div>
    {% endif %}
</div>
{% endblock %}
'''

DATABASE_ADMIN_QUERY_TEMPLATE = '''
{% extends "database_admin_base.html" %}
{% block content %}
<div class="main-content">
    <h2>SQL Query</h2>
    
    <form method="post">
        <textarea name="query" class="query-box" placeholder="Enter your SQL query here...">{{ query or '' }}</textarea>
        <br>
        <button type="submit" class="btn">Execute Query</button>
        <button type="button" onclick="document.querySelector('.query-box').value=''" class="btn btn-danger">Clear</button>
    </form>
    
    {% if result %}
        {% if result.success %}
            {% if result.data %}
                <h3>Query Results</h3>
                <table>
                    <thead>
                        <tr>
                            {% for column in result.data[0].keys() %}
                            <th>{{ column }}</th>
                            {% endfor %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in result.data %}
                        <tr>
                            {% for value in row.values() %}
                            <td>{{ value if value is not none else '<em>NULL</em>' }}</td>
                            {% endfor %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <div class="alert alert-success">{{ result.message }}</div>
            {% endif %}
        {% else %}
            <div class="alert alert-danger">Error: {{ result.error }}</div>
        {% endif %}
    {% endif %}
    
    <h3>Quick Queries</h3>
    <div>
        <a href="{{ url_for('admin_db_query') }}?query=SELECT name FROM sqlite_master WHERE type='table'" class="btn">Show Tables</a>
        <a href="{{ url_for('admin_db_query') }}?query=SELECT * FROM user LIMIT 10" class="btn">View Users</a>
        <a href="{{ url_for('admin_db_query') }}?query=SELECT COUNT(*) as total_users FROM user" class="btn">Count Users</a>
    </div>
</div>
{% endblock %}
'''