
import redis
import os
import random

CACHIAN_REDIS_HOST = os.getenv('CACHIAN_REDIS_HOST', 'localhost')
CACHIAN_REDIS_PORT = int(os.getenv('CACHIAN_REDIS_PORT', '6379'))
CACHIAN_REDIS_DB = int(os.getenv('CACHIAN_REDIS_DB', '0'))
CACHIAN_REDIS_PASSWORD = os.getenv('CACHIAN_REDIS_PASSWORD', '')
CACHIAN_REDIS_SSL = os.getenv('CACHIAN_REDIS_SSL', 'true') == 'true'
CACHIAN_REDIS_NAME = os.getenv('CACHIAN_REDIS_NAME', 'cachian')

redis_client:redis.Redis|None = None


def get_redis_client():
    
    global redis_client
    
    if redis_client is not None:
        return redis_client
    
    if 'redis.azure.net' in CACHIAN_REDIS_HOST:
        from redis_entraid.cred_provider import create_from_managed_identity, ManagedIdentityType
        credential_provider = create_from_managed_identity(
            identity_type=ManagedIdentityType.SYSTEM_ASSIGNED,
            resource="https://redis.azure.com/"
        )
        
        redis_client = redis.Redis(
            host=CACHIAN_REDIS_HOST,
            port=CACHIAN_REDIS_PORT,
            ssl=True,  # SSL is required
            credential_provider=credential_provider,
            decode_responses=True
        )
    else:
        redis_client = redis.StrictRedis(host=CACHIAN_REDIS_HOST, port=CACHIAN_REDIS_PORT, db=CACHIAN_REDIS_DB,
                                    password=CACHIAN_REDIS_PASSWORD, ssl=CACHIAN_REDIS_SSL, decode_responses=True)
        
    # Test connectivity
    rand_key_suffix = str(random.randint(1000,10000))
    test_key = 'TestKey:' + rand_key_suffix
    
    
    # Test locking
    redis_lock = redis_client.lock(test_key, timeout=10) 
    redis_lock.acquire(blocking=True)
    if redis_lock.locked():
        print(f"Successfully acquired Redis test lock: {test_key}")
        redis_lock.release()
    else:
        raise Exception(f"Failed to acquire Redis test lock: {test_key}. Redis might be locked by another process or there is a connectivity issue.")
    
    
    return redis_client
    