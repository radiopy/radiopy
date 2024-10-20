import redis

from src.config import config

config = config["redis"]

cache = dict()

class RedisManager:
    def __init__(self, prefix=""):
        self.prefix = prefix + ":"
        self.used_keys = set()
        self.redis = redis.Redis(**config["connection"])

    def get(self, name):
        """
        Adds a prefix to the key.
        :param name:
        :return:
        """
        name = self.prefix + name
        # check cache first to avoid unnecessary redis calls
        if name in cache:
            return cache[name]
        value = self.redis.get(name)
        # update cache
        if value is not None:
            cache[name] = value
        return value

    def set(self, name, value, ex=config["expiration"]):
        """
        Adds a prefix to the key.
        Adds expiration to the key.
        :param name:
        :param value:
        :param ex:
        :return:
        """
        name = self.prefix + name
        self.redis.set(name, value, ex=ex)
        cache[name] = value

    def rpush(self, name, *values):
        self.redis.rpush(self.prefix + name, *values)
        self.redis.expire(self.prefix + name, config["expiration"])
