import redis
from django.conf import settings

def get_redis_connection():
    """
    Returns a Redis connection object.
    Returns None if connection fails.
    """
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            ssl=settings.REDIS_SSL,
            socket_connect_timeout=5,
            socket_timeout=5,
            decode_responses=True
        )

        # Test connection
        r.ping()
        return r

    except redis.AuthenticationError:
        print("❌ Redis authentication failed")
    except redis.ConnectionError:
        print("❌ Redis connection failed")
    except Exception as e:
        print("❌ Redis error:", e)

    return None