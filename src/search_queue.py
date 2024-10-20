import hashlib
import json

import spotipy
from spotipy import SpotifyOAuth

from config import config
from src.redis_manager import RedisManager, cache

redis = RedisManager("cache")
spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**config["spotify"],
                                                    cache_handler=spotipy.RedisCacheHandler(redis.redis)))


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
    search_term = f"track:{title.strip()}" + (f" artist:{artists.strip()}" if artists else "")
    key = hashlib.sha1((item_id or title).encode()).hexdigest()
    result = redis.get(key)
    if result:
        return json.loads(result)["spotify_id"]
    results = spotify.search(search_term, limit=1, type="track")["tracks"]["items"]
    # edge case. For some reason it works when I send another request
    if results == [None]:
        print("edge case")
        results = spotify.search(search_term, limit=1, type="track")["tracks"]["items"]
    if results:
        cache_entry = {
            "title": title,
            "artists": artists,
            "id": item_id,
            "spotify_id": results[0]["id"],
            "search_term": search_term
        }
        print(results[0]["id"])
    else:
        cache_entry = {
            "title": title,
            "artists": artists,
            "id": item_id,
            "spotify_id": None,
            "search_term": search_term
        }
    redis.set(key, json.dumps(cache_entry))
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
    # delete amount of songs from redis key (in case more get added)
    redis.redis.ltrim(key, len(queue), -1)
    return songs


def main():
    for key in redis.get_song_keys():
        songs = get_all_songs(key)
        if songs:
            redis.rpush(key[:-6] + ":queue", *songs, use_prefix=False)


if __name__ == "__main__":
    main()
