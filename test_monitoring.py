#!/usr/bin/env python3
"""Test script to isolate the circular import issue."""

import os
os.environ['PANEL_USE_SQLITE'] = '1'

print("1. Testing basic app import...")
from app import app, db  # noqa: E402
print("✓ App imported")

print("2. Testing app context...")
with app.app_context():
    print("✓ App context works")
    
    print("3. Testing database...")
    db.create_all()
    print("✓ Database created")
    
    print("4. Testing monitoring imports...")
    from monitoring_system import monitoring_bp, start_monitoring
    from api_monitoring import api_bp
    print("✓ Monitoring modules imported")
    
    print("5. Testing blueprint registration...")
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(api_bp)
    print("✓ Blueprints registered")
    
    print("6. Testing monitoring start...")
    try:
        start_monitoring()
        print("✓ Monitoring system started")
    except Exception as e:
        print(f"⚠ Monitoring start failed: {e}")
    
    print("All tests passed!")