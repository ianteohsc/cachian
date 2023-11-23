from collections.abc import MutableMapping


class MemoryStore(MutableMapping):

    def __init__(self) -> None:
        self.cache_lib = {}

    def __getitem__(self, key):
        return self.cache_lib.get(key)

    def __setitem__(self, key, value):
        self.cache_lib[key] = value

    def __delitem__(self, key):
        del self.cache_lib[key]
    
    def __contains__(self, key):
        return key in self.cache_lib

    def __len__(self):
        return len(self.cache_lib)
    
    def __iter__(self):
        return iter(self.cache_lib)