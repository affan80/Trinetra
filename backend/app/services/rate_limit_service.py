import time
from redis import Redis

class RateLimiter:
    def __init__(self, client: Redis): self.client = client
    def allow(self, source_id, per_minute: int) -> bool:
        key = f"trinetra:rate:{source_id}:{int(time.time() // 60)}"
        count = self.client.incr(key)
        if count == 1: self.client.expire(key, 120)
        return count <= per_minute
