import json

import spotipy

from config import config
from src.redis_manager import RedisManager

redis = RedisManager()

spotify = spotipy.Spotify(auth_manager=spotipy.SpotifyOAuth(**config["spotify"],
                                                            cache_handler=spotipy.RedisCacheHandler(redis.redis)))
user = spotify.me()["id"]


def create_playlists():
    """
    Create playlists from the redis queue.
    :return:
    """
    mapping = json.loads(redis.get("mapping") or "{}")

    # ensure that all playlists exist
    for key in redis.get_keys("queue"):
        key = key[:-6]
        if key in mapping:
            continue
        metadata = redis.get(f"{key}:metadata")
        if not metadata:
            continue
        metadata = json.loads(metadata)
        playlist = spotify.user_playlist_create(user,
                                                metadata["name"],
                                                public=True,
                                                description="radiopy.github.io | " + metadata["description"])
        # TODO: spotify.playlist_upload_cover_image(playlist["id"], metadata["image"])
        mapping[key] = playlist["id"]
        redis.set("mapping", json.dumps(mapping))


def delete_playlists():
    """
    Has to be run before doing anything else that needs mapping.
    Ensure that a channel exists for each playlist.
    If not, the playlist will be unfollowed.
    After a playlist doesn't exist anymore, the mapping will be deleted too.
    :return:
    """
    mapping = json.loads(redis.get("mapping") or "{}")
    for key in mapping:
        try:
            following = spotify.playlist_is_following(playlist_id=mapping[key], user_ids=[user])[0]
        except spotipy.SpotifyException:
            # if playlist doesn't exist anymore, remove mapping
            del mapping[key]
            redis.set("mapping", json.dumps(mapping))
            continue
        if redis.get(f"{key}:metadata"):
            # ensure that we still follow the playlist
            if not following:
                spotify.current_user_follow_playlist(mapping[key])
        else:
            if following:
                spotify.current_user_unfollow_playlist(mapping[key])
            # don't delete the mapping, wait for Spotify to delete the playlist first


def refresh_metadata():
    """
    Refresh metadata for all playlists.
    :return:
    """
    mapping = json.loads(redis.get("mapping") or "{}")
    for key in mapping:
        metadata = json.loads(redis.get(f"{key}:metadata"))
        spotify.playlist_change_details(playlist_id=mapping[key],
                                        description="radiopy.github.io | " + metadata["description"],
                                        name=metadata["name"])


def refresh_songs():
    """
    Refresh songs for all playlists.
    :return:
    """
    mapping = json.loads(redis.get("mapping") or "{}")
    for key in mapping:
        queue = redis.redis.lrange(f"{key}:queue", 0, -1)
        spotify.playlist_replace_items(mapping[key], queue[:100])
        # add remaining songs from queue
        for index in range(100, len(queue), 100):
            spotify.playlist_add_items(mapping[key], queue[index:index + 100])

        # delete processed songs from queue
        redis.redis.ltrim(f"{key}:queue", len(queue), -1)


if __name__ == "__main__":
    print("delete")
    delete_playlists()
    print("create")
    create_playlists()
    print("refresh m")
    refresh_metadata()
    print("refresh s")
    refresh_songs()
