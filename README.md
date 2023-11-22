# Basic Usage

This module provides memoization with LRU, TTL and various clearing utility functions.

```
from cachian import Cachian

class PatientDB:

    @Cachian() #LRU caching defaulting to 10,000 items
    def get_by_id(self, id):
        pass

    @Cachian(maxsize=100) #LRU caching with 100 items
    def get_by_id2(self, id):
        pass        

    @Cachian(ttl=60) #TTL caching with TTL at 60 secs
    def get_latest_10_patient(self):
        pass
    
    #Split cache clearing by first args ie. id
    @Cachian(partition_attr=1)
    def get_by_id3(self, id):
        pass

    #TTL, LRU & partition caching, whichever miss first
    @Cachian(maxsize=100,ttl=60,partition_attr=1)
    def get_by_id4(self,id):
        pass


#Can be used with standalone functions
@Cachian()
def count_patient_name_len(patient_name):
    return len(patient_name)
```
# Utilities


## Get stats
Utilities to obtain statistics on cached methods/functions. Code continues from the **Basic Usage** example.

```
from cachian import global_cache_info
from pprint import pprint

#Print stats of all cached function/methods
pprint(global_cache_info())

#Print stats of a single cached function/method
pprint(count_patient_name_len.cache_info())
```

## Clearing cache
A few clearing utilities to allow selecting clearing of cached items. Code continues from the **Basic Usage** example.

```
from cachian import function_cache_reset_by_class, function_cache_reset, global_cache_reset

#Clear all cached items of all methods in the class
function_cache_reset_by_class(PatientDB)

#Clear cache of a function
function_cache_reset('count_patient_name_len')

#Clear all cached items
global_cache_reset()
```


# Installation

Basic installation
```
pip install Cachian
```

Clone the repository to run unittests.

Installing the **cachetools** package will allow unittest to run benchmarks against cachetools.

```
pip install cachetools
python -m unittest discover -s . -p "*_test.py"
```

# License

Copyright (c) 2023-2025 Ian Teoh

Licensed under the [MIT](https://raw.github.com/tkem/cachetools/master/LICENSE) license

