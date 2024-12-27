import hashlib
import json

import spotipy
from spotipy import SpotifyOAuth

from config import config
from src.log_setup import logging
import src.redis_manager as redis_manager

logger = logging.getLogger(__name__)

metadata = redis_manager.RedisManager()
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**config["spotify"],
                                                    cache_handler=spotipy.RedisCacheHandler(metadata.redis)))

# making sure the cache is in a different database
db = redis_manager.config.get("cache_database")
if db is not None:
    redis_manager.config["connection"]["db"] = db
search = redis_manager.RedisManager("cache")


def fetch_songs(key):
    """
    Fetches a queue from redis.
    :param key:
    :return:
    """
    return metadata.redis.lrange(key, 0, -1)


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
        result = search.get(id_key)
        if result:
            return json.loads(result)["spotify_id"]
    key = hashlib.sha1(search_term.encode()).hexdigest()
    result = search.get(key)
    if result:
        return json.loads(result)["spotify_id"]
    # the search API can't handle percent signs, so we need to escape them (even if requests does it too)
    results = spotify.search(search_term.replace("%", "%25"), limit=1, type="track")["tracks"]["items"]
    # edge case. For some reason it works when I send another request
    if results == [None]:
        logger.warning("Spotify search returned [None]. Trying again.")
        # the search API can't handle percent signs, so we need to escape them (even if requests does it too)
        results = spotify.search(search_term.replace("%", "%25"), limit=1, type="track")["tracks"]["items"]
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
    search.set(key, json.dumps(cache_entry))
    if item_id:
        # noinspection PyUnboundLocalVariable
        search.set(id_key, json.dumps(cache_entry))
    return cache_entry["spotify_id"]


def get_all_songs(key):
    """
    Process the queue for a specific key.
    :param key:
    :return:
    """
    songs = []
    queue = fetch_songs(key)
    for song in queue:
        song = json.loads(song)
        song = search_song(song["title"], song.get("artists"), song.get("id"))
        if song:
            songs.append(song)
    # only delete amount of songs from redis list (in case more get added while processing)
    if queue:
        metadata.redis.ltrim(key, len(queue), -1)
    return songs


def main():
    keys = metadata.get_keys("songs")
    for index, key in enumerate(keys):
        logger.info(f"{index + 1:02d}/{len(keys)}: {key}")
        songs = get_all_songs(key)
        if songs:
            metadata.rpush(key[:-6] + ":queue", *songs, use_prefix=False)


if __name__ == "__main__":
    main()
