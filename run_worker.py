import os
import redis
from rq import Worker, Queue, Connection
import config

listen = ['default']

redis_url = os.environ.get('PANEL_REDIS_URL', config.REDIS_URL)
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
