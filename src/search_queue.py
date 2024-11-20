import argparse
import hashlib
import json
import time

import spotipy
from spotipy import SpotifyOAuth

from config import config
from src.redis_manager import RedisManager
from src.log_setup import logging

logger = logging.getLogger(__name__)
redis = RedisManager("cache")
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**config["spotify"],
                                                    cache_handler=spotipy.RedisCacheHandler(redis.redis)))


def get_timeout() -> [int, None]:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c",
                        "--cron",
                        help="Stop the script after a certain amount of time",
                        type=int,
                        default=0)
    cron = parser.parse_args().cron
    if cron:
        return cron + int(time.time())

TIMEOUT = get_timeout()

def fetch_songs(key):
    """
    Fetches a queue from redis.
    :param key:
    :return:
    """
    return redis.redis.lrange(key, 0, -1)


def search_song(title, artists: str = None, item_id: str = None):
    """
    Search for a song in the redis queue.
    If not found, the song will be searched on Spotify.
    :param title:
    :param artists:
    :param item_id:
    :return:
    """
    search_term = f"track:{title.lower().strip()}" + (f" artist:{artists.lower().strip()}" if artists else "")
    if item_id:
        id_key = hashlib.sha1(item_id.encode()).hexdigest()
        result = redis.get(id_key)
        if result:
            return json.loads(result)["spotify_id"]
    key = hashlib.sha1(search_term.encode()).hexdigest()
    result = redis.get(key)
    if result:
        return json.loads(result)["spotify_id"]
    results = spotify.search(search_term, limit=1, type="track")["tracks"]["items"]
    # edge case. For some reason it works when I send another request
    if results == [None]:
        logger.warning("Spotify search returned [None]. Trying again.")
        results = spotify.search(search_term, limit=1, type="track")["tracks"]["items"]
    if results:
        cache_entry = {
            "title": title,
            "artists": artists,
            "id": item_id,
            "spotify_id": results[0]["id"],
            "search_term": search_term
        }
        logger.info(f"Found song: {results[0]['id']}")
    else:
        cache_entry = {
            "title": title,
            "artists": artists,
            "id": item_id,
            "spotify_id": None,
            "search_term": search_term
        }
    redis.set(key, json.dumps(cache_entry))
    if item_id:
        # noinspection PyUnboundLocalVariable
        redis.set(id_key, json.dumps(cache_entry))
    return cache_entry["spotify_id"]


def get_all_songs(key):
    """
    Process the queue for a specific key.
    :param key:
    :return:
    """
    songs = []
    queue = fetch_songs(key)
    index = 0
    for index, song in enumerate(queue):
        if TIMEOUT and TIMEOUT < int(time.time() - 10):
            logger.info("Timeout reached. Stopping.")
            break

        song = json.loads(song)
        song = search_song(song["title"], song.get("artists"), song.get("id"))
        if song:
            songs.append(song)
    # delete amount of songs from redis key (in case more get added)
    if index:
        redis.redis.ltrim(key, index + 1, -1)
    return songs


def main():
    keys = redis.get_keys("songs")
    for index, key in enumerate(keys):
        logger.info(f"{index+1:02d}/{len(keys)}: {key}")
        songs = get_all_songs(key)
        if songs:
            redis.rpush(key[:-6] + ":queue", *songs, use_prefix=False)


if __name__ == "__main__":
    main()
