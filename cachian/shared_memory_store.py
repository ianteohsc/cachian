"""Gunicorn multi-worker safe in-memory cache store.

Uses multiprocessing.managers to share a dictionary across worker processes.
A manager server is started automatically on first use; subsequent
instantiations in the same or other processes connect to the existing server.

Usage:
    from cachian import Cachian
    from cachian.shared_memory_store import SharedMemoryStore

    @Cachian(cache_class=SharedMemoryStore)
    def my_function(x):
        return expensive_computation(x)

For gunicorn, use --preload so the manager server is started by the master
process before workers are forked:

    gunicorn --preload -w 4 myapp:app

Environment variables:
    CACHIAN_SHM_HOST: Manager server host (default: '127.0.0.1')
    CACHIAN_SHM_PORT: Manager server port (default: 19847)
    CACHIAN_SHM_KEY:  Authentication key (default: 'cachian')

Note: All cached values must be picklable since they are transferred between
processes via the manager connection.
"""

from multiprocessing.managers import BaseManager
from collections.abc import MutableMapping
import os
import time


CACHIAN_SHM_HOST = os.getenv('CACHIAN_SHM_HOST', '127.0.0.1')
CACHIAN_SHM_PORT = int(os.getenv('CACHIAN_SHM_PORT', '19847'))
CACHIAN_SHM_KEY = os.getenv('CACHIAN_SHM_KEY', 'cachian').encode()


class _SharedCache:
    """Dict wrapper with non-dunder public methods for clean proxy access.

    AutoProxy only exposes public (non-underscore) methods, so all dict
    operations are wrapped as regular methods.
    """

    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        self._data[key] = value

    def delete(self, key):
        del self._data[key]

    def contains(self, key):
        return key in self._data

    def length(self):
        return len(self._data)

    def keys(self):
        return list(self._data.keys())

    def clear(self):
        self._data.clear()

    def pop(self, key, *args):
        return self._data.pop(key, *args)


_server_cache = _SharedCache()


def _get_cache():
    return _server_cache


class _CacheManager(BaseManager):
    pass


_CacheManager.register('get_cache', callable=_get_cache)


class SharedMemoryStore(MutableMapping):
    """A gunicorn multi-worker safe in-memory cache store.

    Uses multiprocessing.managers to share a dictionary across worker processes.
    The first process to instantiate SharedMemoryStore starts a manager server;
    subsequent processes connect to the running server.

    Individual dict operations are serialized by the manager server. Compound
    operations (e.g., iterate-then-delete) spanning multiple calls are not
    atomic across processes; for cache use this is acceptable since the worst
    case is a redundant recomputation.
    """

    _manager = None
    _cache = None

    def __init__(self):
        if SharedMemoryStore._cache is not None:
            return
        self._connect_or_start()

    def _connect_or_start(self):
        address = (CACHIAN_SHM_HOST, CACHIAN_SHM_PORT)

        # Try connecting to an existing manager server first
        try:
            manager = _CacheManager(address=address, authkey=CACHIAN_SHM_KEY)
            manager.connect()
            SharedMemoryStore._manager = manager
            SharedMemoryStore._cache = manager.get_cache()
            return
        except (ConnectionRefusedError, ConnectionResetError, EOFError, OSError):
            pass

        # No server running — start one
        try:
            manager = _CacheManager(address=address, authkey=CACHIAN_SHM_KEY)
            manager.start()
            SharedMemoryStore._manager = manager
            SharedMemoryStore._cache = manager.get_cache()
        except OSError:
            # Another process may have started the server between our
            # failed connect and this start attempt — retry connecting
            time.sleep(0.1)
            manager = _CacheManager(address=address, authkey=CACHIAN_SHM_KEY)
            manager.connect()
            SharedMemoryStore._manager = manager
            SharedMemoryStore._cache = manager.get_cache()

    @property
    def _proxy(self):
        return SharedMemoryStore._cache

    def __getitem__(self, key):
        return self._proxy.get(key)

    def __setitem__(self, key, value):
        self._proxy.set(key, value)

    def __delitem__(self, key):
        self._proxy.delete(key)

    def __contains__(self, key):
        return self._proxy.contains(key)

    def __len__(self):
        return self._proxy.length()

    def __iter__(self):
        return iter(self._proxy.keys())

    def pop(self, key, *args):
        return self._proxy.pop(key, *args)

    def clear(self):
        self._proxy.clear()
