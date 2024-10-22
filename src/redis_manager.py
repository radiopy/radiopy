import redis

from src.config import config

config = config["redis"]

cache = dict()

class RedisManager:
    def __init__(self, prefix=""):
        self.prefix = prefix + ":" if prefix else ""
        self.used_keys = set()
        self.redis = redis.Redis(**config["connection"])

    def get(self, name, use_prefix=True, auto_extend=True):
        """
        Adds a prefix to the key.
        :param name:
        :param use_prefix:
        :param auto_extend:
        :return:
        """
        name = self.prefix + name if use_prefix else name
        # check cache first to avoid unnecessary redis calls
        if name in cache:
            return cache[name]
        value = self.redis.get(name)
        # update cache
        if value is not None:
            if auto_extend:
                self.extend(name)
            cache[name] = value
        return value

    def set(self, name, value, ex=config["expiration"], use_prefix=True):
        """
        Adds a prefix to the key.
        Adds expiration to the key.
        :param name:
        :param value:
        :param ex:
        :param use_prefix:
        :return:
        """
        name = self.prefix + name if use_prefix else name
        self.redis.set(name, value, ex=ex)
        cache[name] = value

    def rpush(self, name, *values, use_prefix=True):
        name = self.prefix + name if use_prefix else name
        self.redis.rpush(name, *values)
        self.redis.expire(name, config["expiration"])

    def extend(self, name, ex=config["expiration"], use_prefix=True):
        name = self.prefix + name if use_prefix else name
        self.redis.expire(self.prefix + name, ex)

    def get_keys(self, endswith=""):
        """
        Get all song lists.
        :return:
        """
        return self.redis.keys(f"*:{endswith}")
