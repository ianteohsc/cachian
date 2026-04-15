import os
os.environ["CACHIAN_ENABLE"] = "1"
os.environ["CACHIAN_SHM_PORT"] = "19848"  # Avoid conflict with other tests

import unittest
import multiprocessing
from time import sleep
from cachian import Cachian
from cachian.shared_memory_store import SharedMemoryStore


class SharedMemoryStoreTestCase(unittest.TestCase):

    def setUp(self):
        # Reset class-level state so each test gets a fresh connection
        SharedMemoryStore._manager = None
        SharedMemoryStore._cache = None

    def tearDown(self):
        if SharedMemoryStore._manager is not None:
            try:
                SharedMemoryStore._cache.clear()
            except Exception:
                pass

    def test_basic_get_set(self):
        store = SharedMemoryStore()
        store['key1'] = 'value1'
        self.assertEqual(store['key1'], 'value1')

    def test_missing_key_returns_none(self):
        store = SharedMemoryStore()
        self.assertIsNone(store['nonexistent'])

    def test_contains(self):
        store = SharedMemoryStore()
        store['exists'] = 42
        self.assertIn('exists', store)
        self.assertNotIn('missing', store)

    def test_delete(self):
        store = SharedMemoryStore()
        store['to_delete'] = 'bye'
        del store['to_delete']
        self.assertNotIn('to_delete', store)

    def test_len(self):
        store = SharedMemoryStore()
        store.clear()
        store['a'] = 1
        store['b'] = 2
        self.assertEqual(len(store), 2)

    def test_iter(self):
        store = SharedMemoryStore()
        store.clear()
        store['x'] = 1
        store['y'] = 2
        self.assertEqual(sorted(store), ['x', 'y'])

    def test_clear(self):
        store = SharedMemoryStore()
        store['a'] = 1
        store.clear()
        self.assertEqual(len(store), 0)

    def test_pop(self):
        store = SharedMemoryStore()
        store['popme'] = 'val'
        result = store.pop('popme')
        self.assertEqual(result, 'val')
        self.assertNotIn('popme', store)

    def test_tuple_values(self):
        """Cachian stores (result, timestamp) tuples."""
        store = SharedMemoryStore()
        store['cached'] = ('hello', 1234567890.0)
        result = store['cached']
        self.assertEqual(result, ('hello', 1234567890.0))

    def test_with_cachian_decorator(self):
        @Cachian(cache_class=SharedMemoryStore, test_mode=True)
        def add(a, b):
            return a + b

        add.clear_all()
        self.assertEqual(add(1, 2), 'miss')
        self.assertEqual(add(1, 2), 'hit')
        self.assertEqual(add(2, 3), 'miss')
        self.assertEqual(add(2, 3), 'hit')


def _worker_write(key, value):
    """Helper function run in a child process."""
    store = SharedMemoryStore()
    store[key] = value


def _worker_read(key, result_dict, worker_id):
    """Helper function run in a child process."""
    store = SharedMemoryStore()
    result_dict[worker_id] = store[key]


class SharedMemoryStoreCrossProcessTestCase(unittest.TestCase):

    def setUp(self):
        SharedMemoryStore._manager = None
        SharedMemoryStore._cache = None

    def tearDown(self):
        if SharedMemoryStore._manager is not None:
            try:
                SharedMemoryStore._cache.clear()
            except Exception:
                pass

    def test_cross_process_sharing(self):
        """Write in parent, read in child process."""
        store = SharedMemoryStore()
        store['shared_key'] = 'shared_value'

        manager = multiprocessing.Manager()
        result_dict = manager.dict()

        p = multiprocessing.Process(target=_worker_read, args=('shared_key', result_dict, 0))
        p.start()
        p.join(timeout=10)

        self.assertEqual(result_dict[0], 'shared_value')

    def test_child_write_parent_read(self):
        """Write in child, read in parent process."""
        store = SharedMemoryStore()

        p = multiprocessing.Process(target=_worker_write, args=('from_child', 'child_value'))
        p.start()
        p.join(timeout=10)

        self.assertEqual(store['from_child'], 'child_value')


if __name__ == '__main__':
    unittest.main()
