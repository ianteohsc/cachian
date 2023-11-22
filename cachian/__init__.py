
from pickle import dumps, HIGHEST_PROTOCOL
import os
import gc
from threading import Lock
from time import time
# Fastest hash as per Python 3.9, next best is blake2b
from hashlib import sha3_256 as hashfunc
from functools import lru_cache, partial


DEFAULT_PARTITION_VALUE = 'default'
NUM_PARAM_HASH_CACHED: int = 10000
CACHIAN_ENABLE: bool = int(os.environ.get('CACHIAN_ENABLE', 1)) == 1

if not CACHIAN_ENABLE:
    print('---Cachian DISABLED---')


@lru_cache(NUM_PARAM_HASH_CACHED)
def get_param_hash(*args, **kwargs):

    key1 = dumps(args, HIGHEST_PROTOCOL)
    key2 = dumps(kwargs, HIGHEST_PROTOCOL)

    m = hashfunc()
    m.update(key1+key2)

    return m.hexdigest()


class Cachian():

    ttl: int = -1  # Seconds
    cache_lib = {}
    maxsize: int = -1
    lock: Lock = Lock()
    obj_self = None  # Used for holding self for cached class methods
    partition_attr: str|int = ''

    def __init__(self, *args, **kwargs) -> None:

        self.ttl = kwargs.get('ttl', -1)
        self.maxsize = kwargs.get('maxsize', -1)
        self.test_mode = kwargs.get('test_mode', False)
        self.cache_lib = kwargs.get('cache_lib', {})
        self.partition_attr = kwargs.get('partition_attr', '')

        self.clear_all()

    def __call__(self, func, *args, **kwargs):
        parent = self
        if self.obj_self is None:
            return _CachianWrapper(func, parent)
        else:
            return _CachianWrapper(self.obj_self, func, parent)

    def clear_all(self):
        with self.lock:
            self.cache_lib = {}

    def _length(self):
        return len(self.cache_lib)

    def _full(self):
        if self.maxsize <= 0:
            return False

        return len(self.cache_lib) >= self.maxsize

    # Remove item by FIFO
    def _pop(self):
        first_key = None
        for i in iter(self.cache_lib):
            first_key=i
            break

        return self.cache_lib.pop(first_key)

    def add(self, key, item, partition_value=DEFAULT_PARTITION_VALUE):
        if not CACHIAN_ENABLE:
            return

        with self.lock:
            if self._full():
                self._pop()

            self.cache_lib[f'{partition_value}_{key}'] = item

            pass

    # Must be called after checking with has().
    # get() doesn't check for TTL
    def get(self, key, partition_value=DEFAULT_PARTITION_VALUE):
        with self.lock:
            return self.cache_lib[f'{partition_value}_{key}']

    # Must be called after checking with has().
    # remove() doesn't check for TTL
    def remove_partition(self, partition_value=DEFAULT_PARTITION_VALUE):

        removed = 0
        with self.lock:
            for key in list(self.cache_lib.keys()):
                if partition_value in key:
                    del self.cache_lib[key]
                    removed+=1
        
        return removed

    def set_object_self(self, obj_self):
        self.obj_self = obj_self

    def has2(self, key, partition_value=DEFAULT_PARTITION_VALUE):

        full_key = f'{partition_value}_{key}'

        with self.lock:
            r = self.cache_lib.get(full_key)
            if r is not None:
                if self.ttl > 0:
                    result, ts = r
                    if time() - ts > self.ttl:
                        # Remove so future checks are faster
                        del self.cache_lib[full_key]
                        return None, None  # Key expired based on TTL
                    else:
                        return result, ts  # Key is within TTL
                else:
                    return r  # TTL is not used
            else:
                return None, None  # Key doesn't exist


# Uses InnerClass so both Cachian() and Cachian(ttl=1) format is supported
class _CachianWrapper(object):

    func = None
    parent: Cachian = None
    hit: int = 0
    miss: int = 0
    lifetime_hit: int = 0
    lifetime_miss: int = 0

    def __init__(self, func, parent) -> None:
        self.func = func
        self.parent = parent

    def _get_partition_value(self, *args, **kwargs):

        if isinstance(self.parent.partition_attr,int):
            partition_value = str(args[self.parent.partition_attr])
        elif isinstance(self.parent.partition_attr,str):
            partition_value = str(kwargs.get(self.parent.partition_attr,DEFAULT_PARTITION_VALUE))
        else:
            partition_value = DEFAULT_PARTITION_VALUE

        return partition_value

    def __call__(self, *args, **kwargs):

        key = get_param_hash(*args, **kwargs)
        partition_value = self._get_partition_value(*args, **kwargs)

        result, ts = self.parent.has2(key, partition_value)

        if result is not None:
            self.hit += 1
            self.lifetime_hit += 1

            if self.parent.test_mode:
                return 'hit'
        else:
            result = self.func(*args, **kwargs)
            self._add(key, result, partition_value)
            self.miss += 1
            self.lifetime_miss += 1

            if self.parent.test_mode:
                return 'miss'

        return result

    @property
    def __name__(self):
        return self.func.__name__

    def __get__(self, instance, owner):
        """Crazy magic.

        Turns this Memoized into a descriptor so if @memoize is used on an instance method, as it is an
        attribute of a class, this __get__ gets invoked, transforming that attribute lookup into this partial call
        which adds the memoized object instance to the function call as the first parameter to __call__.

        From https://stackoverflow.com/questions/30104047/how-can-i-decorate-an-instance-method-with-a-decorator-class
        """
        return partial(self.__call__, instance)

    def __instancecheck__(self, other):
        """Make isinstance() work"""
        return isinstance(other, self._f)

    def __len__(self):
        return self.parent._length()

    def _add(self, key, result, partition_value):
        self.parent.add(key, (result, time()), partition_value)

    # def fresh(self, *args, **kwargs):

    #     key = get_param_hash(*args, **kwargs)
    #     partition_value = self._get_partition_value(*args, **kwargs)

    #     self.parent.remove(key, partition_value)
    #     result = self.func(*args, **kwargs)
    #     self._add(key, result, partition_value)

    #     if self.parent.test_mode:
    #         return 'fresh'

    def clear_all(self):
        self.parent.clear_all()
        get_param_hash.cache_clear()

        if self.parent.test_mode:
            return 'cleared'

    def reset(self):
        self.hit = 0
        self.miss = 0
        self.clear_all()

    def clear(self, partition_value):

        removed = self.parent.remove_partition(partition_value)

        if self.parent.test_mode:
            return 'cleared',removed

    def cache_info(self):
        return {'lifetime_hit': self.lifetime_hit, 'hit': self.hit, 'lifetime_miss': self.lifetime_miss, 'miss': self.miss, 'size': len(self), 'ttl_seconds': self.parent.ttl, 'partition_attr': self.parent.partition_attr}

    def function_name(self):
        return self.func.__name__


def get_all_wrappers():

    wrappers = [
        a for a in gc.get_objects()
        if isinstance(a, _CachianWrapper)]

    return wrappers


def function_cache_clear_by_partition(wrapper_name, partition_value):

    for wrapper in get_all_wrappers():
        func_name = str(wrapper.func)
        if wrapper_name in func_name:
            wrapper.clear(partition_value)


def function_cache_reset_by_classname(clsname):

    class_search_str = f'<function {clsname}.'

    func_names = []

    for wrapper in get_all_wrappers():
        func_name = str(wrapper.func)
        if class_search_str in func_name:
            wrapper.clear_all()
            func_names.append(func_name)
    
    return func_names


def function_cache_reset_by_class(cls):

    function_cache_reset_by_classname(cls.__name__)


def function_cache_reset(wrapper_name):

    for wrapper in get_all_wrappers():
        func_name = str(wrapper.func)
        if wrapper_name in func_name:
            return wrapper.clear_all()


def global_cache_reset():
    reset_functions = []

    for wrapper in get_all_wrappers():
        try:
            wrapper.clear_all()
            reset_functions.append(wrapper.function_name())
        except:
            pass


def global_cache_info():

    cache_infos = {}

    for wrapper in get_all_wrappers():
        ci = wrapper.cache_info()
        func_name = str(wrapper.func)
        if cache_infos.get(func_name) is None:
            cache_infos[func_name] = []
        cache_infos[str(wrapper.func)].append(ci)

    return cache_infos
