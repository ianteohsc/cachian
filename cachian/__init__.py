
from pickle import dumps, HIGHEST_PROTOCOL
import os
import gc
from inspect import Parameter, signature
from time import time
# Fastest hash as per Python 3.9, next best is blake2b
from hashlib import sha3_256 as hashfunc
from functools import lru_cache, partial
from dataclasses import dataclass
from typing import Any, Callable, ParamSpec, TypeVar, cast

_ParametersT = ParamSpec('_ParametersT')
_ReturnT = TypeVar('_ReturnT')

DEFAULT_PARTITION_VALUE = '$$'
NUM_PARAM_HASH_CACHED: int = 100000
CACHIAN_ENABLE: bool = int(os.environ.get('CACHIAN_ENABLE', 1)) == 1
CACHIAN_STORE_CLASS = os.environ.get('CACHIAN_STORE_CLASS', 'memory')

if not CACHIAN_ENABLE:
    print('---Cachian DISABLED---')


class CacheMissException(Exception):
    pass


class CacheDisabledException(Exception):
    pass


@lru_cache(NUM_PARAM_HASH_CACHED)
def get_param_hash(*args, **kwargs):

    key1 = dumps(args, HIGHEST_PROTOCOL)
    key2 = dumps(kwargs, HIGHEST_PROTOCOL)

    m = hashfunc()
    m.update(key1+key2)

    return m.hexdigest()


def _skip_first_arg_in_hash(func):

    try:
        parameters = tuple(signature(func).parameters.values())
    except (TypeError, ValueError):
        return False

    if not parameters:
        return False

    first_param = parameters[0]
    return first_param.kind in (
        Parameter.POSITIONAL_ONLY,
        Parameter.POSITIONAL_OR_KEYWORD,
    ) and first_param.name in {'self', 'cls'}


@dataclass
class Cachian():

    ttl: int = -1  # Seconds
    cache_lib = None  # Possible to overwrite to use other backends
    maxsize: int = -1
    obj_self = None  # Used for holding self for cached class methods
    partition_attr: str | int = ''
    cache_class = None
    function_name = ''
    enabled = CACHIAN_ENABLE

    def __init__(self, *args, **kwargs) -> None:

        self.ttl = kwargs.get('ttl', -1)
        self.maxsize = kwargs.get('maxsize', -1)
        self.test_mode = kwargs.get('test_mode', False)
        self.cache_class = kwargs.get('cache_class')
        self.enabled = kwargs.get('enabled', CACHIAN_ENABLE)

        if self.cache_class is None:
            if CACHIAN_STORE_CLASS == 'redis':
                from .redis_store import RedisStore
                self.cache_class = RedisStore
            else:
                from .memory_store import MemoryStore
                self.cache_class = MemoryStore

        self.partition_attr = kwargs.get('partition_attr', '')

    def __call__(self, func: Callable[_ParametersT, _ReturnT]) -> '_CachianWrapper[_ParametersT, _ReturnT]':
        parent = self

        if self.obj_self is None:
            cachian_wrapper = _CachianWrapper(func, parent)
        else:
            cachian_wrapper = _CachianWrapper(self.obj_self, func, parent)

        self.function_name = cachian_wrapper.function_name()

        self._init_cache_class()

        return cachian_wrapper

    def _init_cache_class(self):
        self.cache_lib = self.cache_class(self.function_name.replace(' ', '_'))

    def _supports_iteration(self):
        return getattr(self.cache_lib, 'supports_iteration', True)

    def _supports_clear(self):
        return getattr(self.cache_lib, 'supports_clear', True)

    def clear_all(self):
        if self.cache_lib is None:
            self._init_cache_class()
            return False

        if not self._supports_clear():
            return False

        self.cache_lib.clear()
        return True

    def _length(self):
        if not self._supports_iteration():
            raise NotImplementedError(
                f'{self.cache_lib.__class__.__name__} does not support cache length without key enumeration')

        l = len(self.cache_lib)

        return l

    def _key_partition_str(self, key, partition_value):
        return partition_value + '|' + key

    def add(self, key, item, partition_value=DEFAULT_PARTITION_VALUE):
        if not self.enabled:
            return

        self.cache_lib[self._key_partition_str(key, partition_value)] = item

    # Must be called after checking with has().
    # get() doesn't check for TTL
    def get(self, key, partition_value=DEFAULT_PARTITION_VALUE):
        return self.cache_lib[self._key_partition_str(key, partition_value)]

    # Must be called after checking with has().
    # remove() doesn't check for TTL
    def remove_partition(self, partition_value=DEFAULT_PARTITION_VALUE):

        removed = self.cache_lib.clear_like(partition_value + '|*')

        return removed

    def set_object_self(self, obj_self):
        self.obj_self = obj_self

    def has2(self, key, partition_value=DEFAULT_PARTITION_VALUE):

        if not self.enabled:
            raise CacheDisabledException('Cache disabled')

        r = self.cache_lib.get(self._key_partition_str(key, partition_value))
        if r is not None:
            if self.ttl > 0:
                result, ts = r
                if time() - ts > self.ttl:
                    # Remove so future checks are faster
                    del self.cache_lib[self._key_partition_str(
                        key, partition_value)]
                    raise CacheMissException('Key expired based on TTL')
                else:
                    return result, ts  # Key is within TTL
            else:
                return r  # TTL is not used
        else:
            raise CacheMissException('Key not found')


# Uses InnerClass so both Cachian() and Cachian(ttl=1) format is supported
class _CachianWrapper(Callable[_ParametersT, _ReturnT]):

    func = None
    parent: Cachian = None

    debug: bool = False

    def __init__(self, func: Callable[_ParametersT, _ReturnT], parent: Cachian) -> None:
        self.func = func
        self.parent = parent
        self._skip_first_arg_from_hash = _skip_first_arg_in_hash(func)

    def _get_partition_value(self, *args, **kwargs):

        if isinstance(self.parent.partition_attr, int):
            partition_value = str(args[self.parent.partition_attr])
        elif isinstance(self.parent.partition_attr, str):
            partition_value = str(kwargs.get(
                self.parent.partition_attr, DEFAULT_PARTITION_VALUE))
        else:
            partition_value = DEFAULT_PARTITION_VALUE

        return partition_value

    def __call__(self, *args, **kwargs):

        if not self.parent.enabled:
            return self.func(*args, **kwargs)

        key_args: tuple = (self.function_name(),) + args
        key = get_param_hash(*key_args, **kwargs)
        partition_value = self._get_partition_value(*args, **kwargs)
        return_result = None

        try:
            result, ts = self.parent.has2(key, partition_value)
            if self.parent.test_mode:
                return_result = 'hit'
            else:
                return_result = result

        except CacheDisabledException:
            # Cache disabled, just run the function without caching. Pass through has2 to ensure miss count is tracked
            return_result = self.func(*args, **kwargs)

        except CacheMissException:
            result = self.func(*args, **kwargs)
            self._add(key, result, partition_value)
            if self.parent.test_mode:
                return_result = 'miss'
            else:
                return_result = result

        return return_result

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
        if instance is None:
            return self

        return partial(self.__call__, instance)

    def __instancecheck__(self, other):
        """Make isinstance() work"""
        return isinstance(other, self._f)

    def __len__(self):
        return self.parent._length()

    def _add(self, key, result, partition_value):

        if not self.parent.enabled:
            return

        self.parent.add(key, (result, time()), partition_value)

    def clear_all(self):

        if not self.parent.enabled:
            return

        cleared = self.parent.clear_all()
        get_param_hash.cache_clear()

        if self.parent.test_mode:
            return 'cleared' if cleared else 'unsupported'

    def reset(self):
        self.parent.cache_lib.clear_hits_misses()
        self.clear_all()

    def clear(self, partition_value):

        if not self.parent.enabled:
            return

        removed = self.parent.remove_partition(partition_value)

        if self.parent.test_mode:
            return 'cleared', removed

    def cache_info(self):
        try:
            size = len(self)
        except NotImplementedError:
            size = None

        return {'enabled': self.parent.enabled, 'lifetime_hit': self.parent.cache_lib.lifetime_hits, 'hit': self.parent.cache_lib.hits, 'lifetime_miss': self.parent.cache_lib.lifetime_misses, 'miss': self.parent.cache_lib.misses, 'size': size, 'ttl_seconds': self.parent.ttl, 'partition_attr': self.parent.partition_attr}

    def function_name(self):
        return f'{self.func.__module__} {self.func.__name__}'


def get_all_wrappers():

    wrappers = [
        a for a in gc.get_objects()
        if isinstance(a, _CachianWrapper)]

    return wrappers


@lru_cache(10000)
def _find_wrapper_by_func_name(wrapper_name):
    for wrapper in get_all_wrappers():
        func_name = str(wrapper.func)
        if wrapper_name in func_name:
            return wrapper

    return None


def function_cache_clear_by_partition(wrapper_name, partition_value):

    if not CACHIAN_ENABLE:
        return

    wrapper = _find_wrapper_by_func_name(wrapper_name)

    if wrapper is not None:
        wrapper.clear(partition_value)


def function_cache_reset_by_classname(clsname):

    if not CACHIAN_ENABLE:
        return

    class_search_str = f'<function {clsname}.'

    func_names = []

    for wrapper in get_all_wrappers():
        func_name = str(wrapper.func)
        if class_search_str in func_name:
            wrapper.clear_all()
            func_names.append(func_name)

    return func_names


def function_cache_reset_by_class(cls):

    if not CACHIAN_ENABLE:
        return

    function_cache_reset_by_classname(cls.__name__)


def function_cache_reset(wrapper_name):

    if not CACHIAN_ENABLE:
        return

    for wrapper in get_all_wrappers():
        func_name = str(wrapper.func)
        if wrapper_name in func_name:
            return wrapper.clear_all()


def global_cache_reset():
    reset_functions = []

    if not CACHIAN_ENABLE:
        return


def global_cache_info():

    cache_infos = {}

    for wrapper in get_all_wrappers():
        ci = wrapper.cache_info()
        func_name = str(wrapper.func)
        if cache_infos.get(func_name) is None:
            cache_infos[func_name] = []
        cache_infos[str(wrapper.func)].append(ci)

    return cache_infos
