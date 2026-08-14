from collections.abc import MutableMapping
import fnmatch

class MemoryStore(MutableMapping):
    name = 'memory'
    hit_count = 0
    miss_count = 0
    lifetime_hit = 0
    lifetime_miss = 0

    def __init__(self, name='') -> None:
        self.name = name
        self.cache_lib = {}

    def __getitem__(self, key):
        i = self.cache_lib.get(key)
        if i is not None:
            self.hit()
            return i
        else:
            self.miss()
            return None

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
    
    def hit(self):
        self.hit_count += 1
        self.lifetime_hit += 1
        
    def miss(self):
        self.miss_count += 1
        self.lifetime_miss += 1
        
    @property
    def hits(self):
        return self.hit_count
    
    @property
    def misses(self):
        return self.miss_count
    
    @property
    def lifetime_hits(self):
        return self.lifetime_hit
    
    @property
    def lifetime_misses(self):
        return self.lifetime_miss
    
        
    def clear_hits_misses(self):
        self.hit_count = 0
        self.miss_count = 0
        self.lifetime_hit = 0
        self.lifetime_miss = 0
    
    def keys_like(self, pattern):
        matching_keys = [key for key in self.cache_lib.keys() if fnmatch.fnmatch(key, pattern)]
        return matching_keys
    
    def clear_like(self, pattern):
        count = 0
        matching_keys = self.keys_like(pattern)
        for key in matching_keys:
            del self.cache_lib[key]
            count += 1
            
        return count