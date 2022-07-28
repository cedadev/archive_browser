
# adapted from https://jellis18.github.io/post/2021-11-25-lru-cache/

from typing import OrderedDict, NamedTuple
import time


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
    def __init__(self, func, maxsize, max_expire_period, min_call_time_for_caching, run_based_expire_factor):
        self.__wrapped__ = func
        self.__cache = LruCache(capacity=maxsize)
        self.__hits = 0
        self.__misses = 0
        self.__expired = 0
        self.__max_expire_period = max_expire_period
        self.__min_call_time_for_caching =  min_call_time_for_caching
        self.__run_based_expire_factor = run_based_expire_factor

    def __call__(self, *args, **kwargs):
        call_args = args + tuple(kwargs.items())
        cache_values = self.__cache.get(call_args)
        if cache_values is None:
            self.__misses += 1
            ret, run_time, expire_time = self._run_wrapped(*args, **kwargs)
            if run_time > self.__min_call_time_for_caching: 
                self.__cache.insert(call_args, (ret, run_time, expire_time))
            return ret
        
        ret, last_run_time, expire_time = cache_values 
        if expire_time < time.time():
            self.__expired += 1
            ret, run_time, expire_time = self._run_wrapped(*args, **kwargs)
            self.__cache.insert(call_args, (ret, run_time, expire_time))
        else:
            self.__hits += 1
        return ret

    def expire_time(self, run_time):
        run_based_expire_time = time.time() + run_time * self.__run_based_expire_factor
        expire_time = time.time() + self.__max_expire_period
        return min(run_based_expire_time, expire_time)

    def _run_wrapped(self, *args, **kwargs):
        start = time.time()
        ret = self.__wrapped__(*args, **kwargs)
        run_time = time.time() - start
        expire_time = self.expire_time(run_time)
        return ret, run_time, expire_time

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
  

def lru_cache_expires(maxsize=1024, max_expire_period=3600 , min_call_time_for_caching=0.0, run_based_expire_factor=1000): 
    def decorator(func):
        return _LruCacheFunctionWrapper(func, maxsize, max_expire_period, min_call_time_for_caching, run_based_expire_factor)
    return decorator