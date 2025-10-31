# adapted from https://jellis18.github.io/post/2021-11-25-lru-cache/

from typing import OrderedDict, NamedTuple
import time
import threading
import queue
import random
import sys


class CacheInfo(NamedTuple):
    hits: int
    misses: int
    expired: int
    maxsize: int
    currsize: int


class LruCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.__cache = OrderedDict()

    def get(self, key):
        if key not in self.__cache:
            return None
        self.__cache.move_to_end(key)
        return self.__cache[key]

    def insert(self, key, value):
        if len(self.__cache) == self.capacity:
            self.__cache.popitem(last=False)
        self.__cache[key] = value
        self.__cache.move_to_end(key)

    def __len__(self):
        return len(self.__cache)

    def clear(self):
        self.__cache.clear()

    def clear_key(self, key):
        if key in self.__cache:
            del self.__cache[key]


class _LruCacheFunctionWrapper:
    def __init__(self, func, maxsize, max_expire_period, default):
        self.__wrapped__ = func
        self.__cache = LruCache(capacity=maxsize)
        self.__hits = 0
        self.__misses = 0
        self.__expired = 0
        self.default = default
        self.__max_expire_period = max_expire_period
        self.queue = queue.Queue(maxsize=1000)
        self.run_thread = threading.Thread(target=self.run_queued, daemon=True)
        self.run_thread.start()

    def __call__(self, arg):
        cache_values = self.__cache.get(arg)
        if cache_values is None:
            self.__misses += 1
            self.queue.put(arg)
            return self.default

        ret, expire_time = cache_values  
        if expire_time < time.time():
            self.__expired += 1
            self.queue.put(arg)
        else:
            self.__hits += 1

        return ret

    def run_queued(self):
        while True:
            arg = self.queue.get()   
            try:      
                ret = self.__wrapped__(arg)
            except Exception as e:
                sys.stderr.write(f"Excption running function {self.__wrapped__} with argument {arg}\n")
                sys.stderr.write(f"{e} {sys.exc_info()}\n")
                sys.stderr.write("continuing.\n")
                continue

            expire_time = time.time() + (1 + 0.2 * random.random()) * self.__max_expire_period 
            self.__cache.insert(arg, (ret, expire_time))

    def cache_info(self) -> CacheInfo:
        return CacheInfo(
            hits=self.__hits,
            misses=self.__misses,
            expired=self.__expired,
            currsize=len(self.__cache),
            maxsize=self.__cache.capacity,
        )

    def cache_clear(self) -> None:
        self.__cache.clear()
        self.__hits = 0
        self.__misses = 0 
        self.__expired = 0 

    def cache_clear_key(self, *args, **kwargs):
        call_args = args + tuple(kwargs.items())
        self.__cache.clear_key(call_args)
  

def lru_cache_expires(maxsize=1024, max_expire_period=3600, default=None): 
    def decorator(func):
        return _LruCacheFunctionWrapper(func, maxsize, max_expire_period, default)
    return decorator