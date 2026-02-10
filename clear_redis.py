import redis

# REDIS_HOST = "common-redis.redis.cache.windows.net"
# REDIS_PASSWORD = "8Jv8fZgUOfNVJVgLwpdpy42blBm7Jx4CmAzCaEjtFdk="
# REDIS_PORT = 6380
REDIS_HOST = "34.100.171.181"
REDIS_PASSWORD = "Bariflo@2025"
REDIS_PORT = 6379

def clear_redis_data():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0,password=REDIS_PASSWORD, ssl=True)
    r.flushdb()
    print("All data cleared from Redis")

if __name__ == "__main__":
    clear_redis_data()
