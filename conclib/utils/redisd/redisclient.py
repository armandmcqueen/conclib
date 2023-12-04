import redis
from conclib import ConclibConfig

from typing import Optional


class RedisClient:
    def __init__(self, config: ConclibConfig):
        self.config = config
        self.redis_client = redis.Redis(
            host=self.config.redis_host, port=self.config.redis_port
        )
        self._pubsub: Optional[redis.client.PubSub] = None

    @property
    def pubsub(self) -> redis.client.PubSub:
        if self._pubsub is None:
            self._pubsub = self.redis_client.pubsub()
        return self._pubsub
