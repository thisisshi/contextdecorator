import sys
import logging

from cache import CacheEngine, RedisConfig, SqliteConfig

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    datefmt='%m-%d %H:%M',
)

redis_config = RedisConfig(host='localhost', port=6379, db=0)
RedisCache = CacheEngine()
RedisCache.set_connection('redis', redis_config)


@RedisCache
def cached_redis_function(key, arg2='redis'):
    return key + 'hello' + arg2


for i in range(10):
    val = cached_redis_function(sys.argv[1])

sqlite_config = SqliteConfig(cache_file='/home/winebaths/tmp/tmp_cache')
SqliteCache = CacheEngine()
SqliteCache.set_connection('sqlite', sqlite_config)


@SqliteCache
def cached_sqlite_function(key, arg2='sqlite'):
    return key + 'hello' + arg2


for i in range(10):
    val = cached_sqlite_function(sys.argv[1], 'world')

RedisCache.flush()
SqliteCache.flush()
