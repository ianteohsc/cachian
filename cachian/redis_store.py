import redis
import json
from collections.abc import MutableMapping
import os

CACHIAN_REDIS_HOST = os.getenv('CACHIAN_REDIS_HOST', 'localhost')
CACHIAN_REDIS_PORT = os.getenv('CACHIAN_REDIS_PORT', '6379')
CACHIAN_REDIS_DB = int(os.getenv('CACHIAN_REDIS_DB', '0'))
CACHIAN_REDIS_PASSWORD = os.getenv('CACHIAN_REDIS_PASSWORD', '')
CACHIAN_REDIS_SSL = os.getenv('CACHIAN_REDIS_SSL', 'true') == 'true'
CACHIAN_REDIS_NAME = os.getenv('CACHIAN_REDIS_NAME', 'cachian')

class RedisStore(MutableMapping):

    def __init__(self):
        self.name = CACHIAN_REDIS_NAME
        self.redis = redis.StrictRedis(host=CACHIAN_REDIS_HOST, port=CACHIAN_REDIS_PORT, db=CACHIAN_REDIS_DB, password=CACHIAN_REDIS_PASSWORD, ssl=CACHIAN_REDIS_SSL, decode_responses=True)

        if len(self)>0:
            self.clear()

    def __getitem__(self, key):
        value = self.redis.hget(self.name, key)
        if value is not None:
            return json.loads(value)
        raise KeyError(key)

    def __setitem__(self, key, value):
        self.redis.hset(self.name, key, json.dumps(value))

    def __delitem__(self, key):
        if self.redis.hdel(self.name, key) == 0:
            raise KeyError(key)

    def __contains__(self, key):
        return self.redis.hexists(self.name, key)

    def __len__(self):
        return self.redis.hlen(self.name)
    
    def __iter__(self):
        return iter(self.redis.hkeys(self.name))

    def keys(self):
        return self.redis.hkeys(self.name)

    def values(self):
        return [json.loads(value) for value in self.redis.hvals(self.name)]

    def items(self):
        return [(key, json.loads(value)) for key, value in self.redis.hgetall(self.name).items()]

    def clear(self):
        self.redis.delete(self.name)