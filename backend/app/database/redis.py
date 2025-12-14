
import redis.asyncio as Redis
import os

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_db = int(os.getenv("REDIS_DB", 0))
redis_max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", 10))


redis_conn_pool = None

def init_pool():
    global redis_conn_pool
    if redis_conn_pool is None:
        redis_conn_pool = Redis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            max_connections=redis_max_connections
        )

def get_redis_connection():
    global redis_conn_pool
    if redis_conn_pool is None:
        init_pool()

    return Redis.Redis(connection_pool=redis_conn_pool)
