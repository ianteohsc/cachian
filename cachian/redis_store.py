import pickle
import redis
from collections.abc import MutableMapping
import os
import random
import glob
import base64

CACHIAN_REDIS_HOST = os.getenv('CACHIAN_REDIS_HOST', 'localhost')
CACHIAN_REDIS_PORT = os.getenv('CACHIAN_REDIS_PORT', '6379')
CACHIAN_REDIS_DB = int(os.getenv('CACHIAN_REDIS_DB', '0'))
CACHIAN_REDIS_PASSWORD = os.getenv('CACHIAN_REDIS_PASSWORD', '')
CACHIAN_REDIS_SSL = os.getenv('CACHIAN_REDIS_SSL', 'true') == 'true'
CACHIAN_REDIS_NAME = os.getenv('CACHIAN_REDIS_NAME', 'cachian')

NONE_VALUE = '!--NONE--!' # Redis does not support storing None, so we store a placeholder string and convert it back to None when retrieving.

redis_client:redis.Redis

class RedisStore(MutableMapping):
    name = ''
    _redis:redis.Redis

    def __init__(self, name=''):
        self.name = name or CACHIAN_REDIS_NAME
        self.name = f'DB{CACHIAN_REDIS_DB}:{self.name}' #Simulate multiple DB by using different hash names, since Azure Redis does not support multiple DBs. This way we can have separate namespaces for different environments or purposes.
        
        global redis_client
        
        if redis_client is None:
            from redis_client_helper import get_redis_client
            redis_client = get_redis_client()

            rand_key_suffix = str(random.randint(1000,10000))
            test_key = 'TestKey:' + rand_key_suffix
            test_value = 'TestValue:' + rand_key_suffix
            
            print('Testing Redis connectivity with key:', test_key, 'and value:', test_value)
            redis_client.hset(self.name, test_key, test_value)
            retrieved_value = redis_client.hget(self.name, test_key)
            
            if test_value != retrieved_value:
                raise Exception('Failed to connect to Redis store. Test key not found or value mismatch.')
            
            redis_client.hdel(self.name, test_key)


        self._redis = redis_client

    def _pickle_to_str(self, value):
        # Redis stores strings, so we need to pickle the value and then convert it to a base64 then to ascii
        return base64.b64encode(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)).decode('ascii')
                   
    def _pickle_from_str(self, value):
        return pickle.loads(base64.b64decode(value.encode('ascii')))

    def __getitem__(self, key):
        
        if self._redis is None:
            raise Exception('Redis client is not initialized.')
        
        value = self._redis.hget(self.name, key)
        if value is not None:
            self.hit()
            unpickled = self._pickle_from_str(value)
            
            if unpickled[0] == NONE_VALUE:
                return (None, unpickled[1])
            else:
                return unpickled
            
        else:
            self.miss()
            return None

    def __setitem__(self, key, value):
        to_pickle = None
        
        if value[0] is None:
            to_pickle = (NONE_VALUE,value[1])
        else:
            to_pickle = value

        self._redis.hset(self.name, key, self._pickle_to_str(to_pickle))

    def __delitem__(self, key):
        if self._redis.hdel(self.name, key) == 0:
            raise KeyError(key)

    def __contains__(self, key):
        return self._redis.hexists(self.name, key)

    def __len__(self):
        return self._redis.hlen(self.name)

    def __iter__(self):
        return iter(self._redis.hkeys(self.name))
    
    def hit(self):
        self._redis.hincrby(self.name, 'hit', 1)
        self._redis.hincrby(self.name, 'lifetime_hit', 1)
    
    def miss(self):
        self._redis.hincrby(self.name, 'miss', 1)
        self._redis.hincrby(self.name, 'lifetime_miss', 1)
        
    @property
    def hits(self):
        return int(self._redis.hget(self.name, 'hit') or 0)
    
    @property
    def misses(self):
        return int(self._redis.hget(self.name, 'miss') or 0)
    
    @property
    def lifetime_hits(self):
        return int(self._redis.hget(self.name, 'lifetime_hit') or 0)
    
    @property
    def lifetime_misses(self):
        return int(self._redis.hget(self.name, 'lifetime_miss') or 0)
    
    def clear_hits_misses(self):
        self._redis.hset(self.name, 'hit', 0)
        self._redis.hset(self.name, 'miss', 0)
        self._redis.hset(self.name, 'lifetime_hit', 0)
        self._redis.hset(self.name, 'lifetime_miss', 0)

    def keys(self):
        return self._redis.hkeys(self.name)
    
    def keys_like(self, pattern):
        # Redis does not support pattern matching for hash keys, so we need to get all keys and filter them in Python
        all_keys = self._redis.hkeys(self.name)
        
        # Check pattern by glob style matching, where * matches any number of characters and ? matches a single character
        matching_keys = [key for key in all_keys if glob.fnmatch.fnmatch(key, pattern)]
        return matching_keys
    
    def clear_like(self, pattern):
        # Get all keys that match the pattern and delete them
        matching_keys = self.keys_like(pattern)
        if matching_keys:
            self._redis.hdel(self.name, *matching_keys)

    def values(self):
        return [self._pickle_from_str(value) for value in self._redis.hvals(self.name)]

    def items(self):
        kv_tuple = [(key, self._pickle_from_str(value))
                    for key, value in self._redis.hgetall(self.name).items()]

        return kv_tuple

    def clear(self):
        for k in self.keys():
            self._redis.hdel(self.name, k)
