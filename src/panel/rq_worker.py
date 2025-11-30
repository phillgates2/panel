#!/usr/bin/env python3
"""
RQ Worker Script for Panel Background Jobs

Run with: python rq_worker.py
"""

import os
import sys

from redis import Redis
from rq import Connection, Queue, Worker

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import job functions
from background_jobs import (backup_queue, default_queue, maintenance_queue,
                             notification_queue)

# Redis connection
redis_url = os.environ.get("PANEL_REDIS_URL", "redis://127.0.0.1:6379/0")
redis_conn = Redis.from_url(redis_url)

# Listen to all queues
listen = ["high", "default", "backup", "notification", "maintenance"]

if __name__ == "__main__":
    with Connection(redis_conn):
        worker = Worker(map(Queue, listen), connection=redis_conn)
        worker.work()
