#!/usr/bin/env python3
"""
Celery Worker Runner
Starts the Celery worker for asynchronous task processing
"""

import os
import sys

# Add app path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == '__main__':
    from src.panel.celery_app import celery_app

    # Run Celery worker
    celery_app.start()