import logging
import json
import redis


class SqliteConfig(object):
    def __init__(self, cache_file):
        self.cache_file = cache_file

    def __repr__(self):
        return 'SqliteConfig(cache_file=%s)' % (self.cache_file)


class RedisConfig(object):
    def __init__(self, host, port, db):
        self.host = host
        self.port = port
        self.db = db

    def __repr__(self):
        return 'RedisConfig(host=%s,port=%s,db=%s)' % (self.host, self.port, self.db)


class CacheEngine(object):
    def __init__(self):
        """
        Cache Engine

        engine_type is one of: 'redis' or 'sqlite'
        engine_config is one of:
          - redis:
            {'redis_host': str, 'redis_port: int}
          - sqlite:
            {'ldap_cache_file': str}
        """
        self.log = logging.getLogger(__name__)
        self.connection = None

    def set_connection(self, engine_type, config):
        self.log.info('Using config: %s' % config)
        if engine_type == 'redis':
            try:
                self.connection = Redis(host=config.host, port=config.port, db=config.db)
            except redis.exceptions.ConnectionError:
                self.log.error('Unable to connect to Redis')
                self.connection = None
        elif engine_type == 'sqlite':
            try:
                import sqlite3 # noqa
            except ImportError:
                raise RuntimeError('No sqlite available: stackoverflow.com/q/44058239')
            self.connection = LocalSqlite(config.cache_file)

    def __call__(self, f):
        """
        Caches calls to the function with the `key` argument and stores the return
        value in redis or sqlite
        """
        def call(*args, **kwargs):
            key = json.dumps(args)
            self.log.debug('Getting cached value with key: %s' % key)
            try:
                result = self.get(key)
            except Exception as e:
                self.log.error('Unable to get value from cache: %s' % e)
                result = None

            if result is not None:
                self.log.debug('Found cached value: %s for: %s' % (result, key))
                return result
            else:
                self.log.debug('No value found for: %s' % key)

            result = f(*args, **kwargs)

            self.log.debug('Setting cache, key:%s value:%s' % (key, result))

            try:
                self.set(key, result)
            except Exception:
                self.log.error(
                    'Unable to set cache for %s, %s. Skipping.' % (key, result))

            return result

        if not self.connection:
            return f

        return call

    def get(self, key):
        if not hasattr(self.connection, 'get'):
            return None
        return self.connection.get(key)

    def set(self, key, value):
        if not hasattr(self.connection, 'set'):
            return None
        return self.connection.set(key, value)

    def flush(self):
        self.log.warning('Flushing cache...')
        try:
            self.connection.flush()
        except Exception as e:
            self.log.error('Unable to flush cache, excception: %s' % e)


class Redis(CacheEngine):
    def __init__(self, host, port=6379, db=0):
        super(Redis, self).__init__()
        self.connection = redis.StrictRedis(host=host, port=port, db=db)

    def get(self, key):
        cache_value = self.connection.get(key)
        if cache_value:
            return json.loads(cache_value)
        else:
            return None

    def set(self, key, value):
        # redis can't write complex python objects like dictionaries as
        # values (the way memcache can) so we turn our dict into a json
        # string when setting, and json.loads when getting

        return self.connection.set(key, json.dumps(value))

    def flush(self):
        self.connection.flushall()


class LocalSqlite(CacheEngine):
    # Use sqlite as a local cache for folks not running the mailer in lambda,
    # avoids extra daemons as dependencies. This normalizes the methods to
    # set/get functions, so you can interchangeable decide which caching system
    # to use, a local file, or memcache, redis, etc If you don't want a redis
    # dependency and aren't running the mailer in lambda this works well

    def __init__(self, file_name):
        import sqlite3
        super(LocalSqlite, self).__init__()
        self.connection = sqlite3.connect(file_name)
        self.connection.execute('''CREATE TABLE IF NOT EXISTS ldap_cache(key text, value text)''')

    def get(self, key):
        sqlite_result = self.connection.execute("select * FROM ldap_cache WHERE key=?", (key,))
        result = sqlite_result.fetchall()
        if len(result) != 1:
            self.log.error(
                'Did not get 1 result from sqlite, something went wrong with key: %s' % key)
            return None
        return json.loads(result[0][1])

    def set(self, key, value):
        # note, the ? marks are required to ensure escaping into the database.
        self.connection.execute("INSERT INTO ldap_cache VALUES (?, ?)", (key, json.dumps(value)))
        self.connection.commit()

    def flush(self):
        self.connection.execute("DROP TABLE ldap_cache")
        self.connection.commit()
