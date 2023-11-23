import os
os.environ["CACHIAN_DEBUG"] = "1"
os.environ["CACHIAN_ENABLE"] = "1"

from dotenv import load_dotenv
load_dotenv()


from datetime import datetime, timedelta
from functools import lru_cache
from time import sleep,perf_counter
import unittest
from cachian import Cachian, function_cache_clear_by_partition
from uuid import uuid4

TTL_SECONDS = 5

class Dummy:

    @Cachian(partition_attr=1,test_mode=True)
    def get_id(self,key,value):
        return f'{key}_{value}'
    
    @lru_cache
    def get_id_lru(self,key,value):
        return f'{key}_{value}'
    

from cachian.redis_store import RedisStore

class DummyRedis:
    @Cachian(cache_class=RedisStore,test_mode=True)
    def get_id_redis(self,key,value):
        return f'{key}_{value}'
        
      

class CachianRedisBackendTestCase(unittest.TestCase):

    def setUp(self) -> None:
        return super().setUp()    

    def test_get_set(self):

        dummy = DummyRedis()
        
        self.assertEqual(dummy.get_id_redis('jkl','1'), 'miss')
        self.assertEqual(dummy.get_id_redis('jkl','1'), 'hit')
        self.assertEqual(dummy.get_id_redis('yui','1'), 'miss')
        self.assertEqual(dummy.get_id_redis('yui','1'), 'hit')    


    def test_cache_benchmark(self):

        run_count = 5000000
        prime_cache_items = 10000

        dummy = DummyRedis()

        @lru_cache
        def add_lru(a, b):
            return a+b
        n=0
        for i in range(prime_cache_items):
            add_lru(i,i)

        before=perf_counter()
        while n< run_count:
            add_lru(2,2)
            n+=1

        after=perf_counter()
        lru_duration = after-before
        print('functools lru_cache: ' + str(lru_duration))



        n=0
        for i in range(prime_cache_items):
            dummy.get_id_redis(str(i)+'_key',str(i)+'_value')

        before=perf_counter()
        while n< run_count:
            dummy.get_id_redis('1_key','1_value')
            n+=1

        after=perf_counter()
        cachian_duration = after-before
        print('Cachian Redis: ' + str(cachian_duration))   

class CachianParitionTestCase(unittest.TestCase):

    def setUp(self) -> None:
        return super().setUp()
        

    def test_get_set(self):

        dummy = Dummy()
        
        self.assertEqual(dummy.get_id('jkl','1'), 'miss')
        self.assertEqual(dummy.get_id('jkl','1'), 'hit')
        self.assertEqual(dummy.get_id('yui','1'), 'miss')
        self.assertEqual(dummy.get_id('yui','1'), 'hit')

    def test_get_clear(self):

        dummy = Dummy()

        self.assertEqual(dummy.get_id('abc','1'), 'miss')
        self.assertEqual(dummy.get_id('abc','1'), 'hit')
        self.assertEqual(dummy.get_id('xyz','1'), 'miss')
        self.assertEqual(dummy.get_id('xyz','1'), 'hit')
        function_cache_clear_by_partition('Dummy.get_id','abc')
        self.assertEqual(dummy.get_id('abc','1'), 'miss')
        self.assertEqual(dummy.get_id('xyz','1'), 'hit')


    def test_benchmark_partition(self):
        run_count = 5000000
        prime_cache_items = 10000

        dummy = Dummy()
        key_const = str(uuid4())
        value_const = str(uuid4())


        n=0
        for i in range(prime_cache_items):
            dummy.get_id_lru(str(i)+'_'+ key_const,str(i)+'_'+value_const)

        before=perf_counter()
        while n< run_count:
            dummy.get_id_lru('1_'+key_const,'1_'+value_const)
            n+=1

        after=perf_counter()
        lru_duration = after-before
        print('functools lru_cache: ' + str(lru_duration))        



        n=0
        for i in range(prime_cache_items):
            dummy.get_id(str(i)+'_key',str(i)+'_value')

        before=perf_counter()
        while n< run_count:
            dummy.get_id('1_key','1_value')
            n+=1

        after=perf_counter()
        cachian_duration = after-before
        print('Cachian: ' + str(cachian_duration))   



class CachianTestCase(unittest.TestCase):

    def setUp(self) -> None:

        @Cachian(test_mode=True)
        def add(a, b):
            return a+b
            
        @Cachian(ttl=TTL_SECONDS,maxsize=100,test_mode=True)
        def add_with_ttl(a, b):
            return a+b

        self.add = add
        self.add_with_ttl = add_with_ttl

        return super().setUp()

    def test_get_set(self):

        add = self.add

        add.clear_all()

        self.assertEqual(add(1, 2), 'miss')
        self.assertEqual(add(1, 2), 'hit')
        self.assertEqual(add(2, 2), 'miss')
        self.assertEqual(add.clear_all(), 'cleared')
        self.assertEqual(add(2, 2), 'miss')
        self.assertEqual(add(1, 2), 'miss')
        self.assertEqual(add(2, 2), 'hit')

    def test_clear_blank_cache(self):

        add = self.add

        add.debug = True

        self.assertEqual(add.clear_all(), 'cleared')
        self.assertEqual(add(2, 2), 'miss')
        self.assertEqual(add.clear_all(), 'cleared')

    def test_cache_length(self):

        add = self.add
        self.assertEqual(add(2, 2), 'miss')
        self.assertEqual(len(add), 1)
        add.clear_all()
        self.assertEqual(len(add), 0)

    def test_cache_ttl(self):

        add_with_ttl = self.add_with_ttl
        add = self.add
        self.assertEqual(add_with_ttl(2, 2), 'miss')
        self.assertEqual(add(2, 2), 'miss')
        sleep(TTL_SECONDS+2)
        self.assertEqual(add_with_ttl(2, 2), 'miss')
        self.assertEqual(add(2, 2), 'hit')
        sleep(1)
        self.assertEqual(add_with_ttl(2, 2), 'hit')
        self.assertEqual(add(2, 2), 'hit')


    def test_cache_benchmark(self):

        run_count = 5000000
        prime_cache_items = 10000

        @lru_cache
        def add_lru(a, b):
            return a+b
        n=0
        for i in range(prime_cache_items):
            add_lru(i,i)

        before=perf_counter()
        while n< run_count:
            add_lru(2,2)
            n+=1

        after=perf_counter()
        lru_duration = after-before
        print('functools lru_cache: ' + str(lru_duration))



        add = self.add_with_ttl
        n=0
        for i in range(prime_cache_items):
            add(i,i)
        before=perf_counter()
        while n< run_count:
            add(2,2)
            n+=1

        after=perf_counter()
        cachian_duration = after-before
        print('Cachian: ' + str(cachian_duration))
        self.assertLess(cachian_duration,lru_duration*14,"Cachian performance dropped more than 1.3x from expected result.")


        try:
            from cachetools import cached, TTLCache
            cache = TTLCache(maxsize=10, ttl=timedelta(hours=12), timer=datetime.now)

            @cached(cache=cache)
            def add_lru_cachetool(a, b):
                return a+b

            n=0
            for i in range(prime_cache_items):
                add_lru_cachetool(i,i)
            before=perf_counter()
            while n< run_count:
                add_lru_cachetool(2,2)
                n+=1

            after=perf_counter()
            cachetools_lru_duration = after-before
            print('cachetools lru_cache: ' + str(cachetools_lru_duration))
            print('Cachian vs cachetools lru_cache: ' + str(cachian_duration/cachetools_lru_duration))
        except:
            print('cachetools package not installed. Run "pip install cachetools" to install and see benchmark results.')



        #Cachian is expected to perform between 11-13x slower than python lru_cache
        print('Cachian vs lru_cache: ' + str(cachian_duration/lru_duration))

    def test_cache_info(self):
        add = self.add

        self.assertEqual(add(1, 2), 'miss')
        self.assertEqual(add(1, 2), 'hit')
        self.assertEqual(add(2, 2), 'miss')

        result = add.cache_info()
        self.assertEqual(result, result|{'hit':1,'miss':2,'size':2})

        self.assertEqual(add.clear_all(), 'cleared')
        self.assertEqual(add(2, 2), 'miss')
        self.assertEqual(add(1, 2), 'miss')
        self.assertEqual(add(2, 2), 'hit')

        result = add.cache_info()
        self.assertEqual(result, result|{'hit':2,'miss':4,'size':2})
    

    def test_cache_reset(self):

        add = self.add

        self.assertEqual(add(1, 2), 'miss')
        self.assertEqual(add(1, 2), 'hit')
        self.assertEqual(add(2, 2), 'miss')

        result = add.cache_info()
        self.assertEqual(result, result|{'hit':1,'miss':2,'size':2})
        
        add.reset()

        result = add.cache_info()
        self.assertEqual(result, result|{'hit':0,'miss':0,'size':0})


    def test_function_name(self):

        add = self.add
        self.assertEqual(add.function_name(), 'add')