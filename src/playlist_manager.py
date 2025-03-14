import json

import spotipy

from config import config
from src.log_setup import logging
from src.redis_manager import RedisManager

logger = logging.getLogger(__name__)
redis = RedisManager()
spotify = spotipy.Spotify(auth_manager=spotipy.SpotifyOAuth(**config["spotify"],
                                                            cache_handler=spotipy.RedisCacheHandler(redis.redis)),
                          # increase timeout to avoid constant errors
                          requests_timeout=10,
                          retries=5)
user = spotify.me()["id"]


def create_playlists(mapping=None):
    """
    Create playlists from the redis queue.
    :return:
    """
    if mapping is None:
        # TODO: make sure that mapping doesn't expire
        mapping = json.loads(redis.get("mapping") or "{}")

    # ensure that all playlists exist
    for key in redis.get_keys("metadata"):
        key = key[:-9]
        if key in mapping:
            continue
        metadata = redis.get(f"{key}:metadata", auto_extend=False)
        if not metadata:
            continue
        metadata = json.loads(metadata)
        if metadata.get("type") != "playlist":
            continue
        logger.info("creating playlist", metadata["name"])
        playlist = spotify.user_playlist_create(user,
                                                metadata["name"],
                                                public=True,
                                                description="radiopy.github.io | " + metadata["description"])
        # TODO: spotify.playlist_upload_cover_image(playlist["id"], metadata["image"])
        mapping[key] = playlist["id"]
        redis.set("mapping", json.dumps(mapping))


def delete_playlists(mapping=None):
    """
    Has to be run before doing anything else that needs mapping.
    Ensure that a channel exists for each playlist.
    If not, the playlist will be unfollowed.
    After a playlist doesn't exist anymore, the mapping will be deleted too.
    :return: A list with all mappings that aren't marked for deletion
    """
    result = {}
    if mapping is None:
        # TODO: make sure that mapping doesn't expire
        mapping = json.loads(redis.get("mapping") or "{}")
    for key in mapping.copy():
        try:
            following = spotify.playlist_is_following(playlist_id=mapping[key], user_ids=[user])[0]
        except spotipy.SpotifyException:
            # if playlist doesn't exist anymore, remove mapping
            del mapping[key]
            redis.set("mapping", json.dumps(mapping))
            continue

        delete = False
        metadata = redis.get(f"{key}:metadata", auto_extend=False)
        if not metadata:
            delete = True
        else:
            metadata = json.loads(metadata)
            if metadata.get("type") != "playlist":
                delete = True
        if delete:
            if following:
                logger.info("unfollowing playlist", mapping[key])
                spotify.current_user_unfollow_playlist(mapping[key])
            # don't delete the mapping, wait for Spotify to delete the playlist first
        else:
            result[key] = mapping[key]
            # ensure that we still follow the playlist
            if not following:
                logger.info("following playlist", mapping[key])
                spotify.current_user_follow_playlist(mapping[key])
    return result


def refresh_metadata(mapping=None):
    """
    Refresh metadata for all playlists.
    :return:
    """
    if mapping is None:
        # TODO: make sure that mapping doesn't expire
        mapping = json.loads(redis.get("mapping") or "{}")
    logger.info(f"refreshing {len(mapping)} playlists")
    for key in mapping:
        metadata = json.loads(redis.get(f"{key}:metadata", auto_extend=False))
        spotify.playlist_change_details(playlist_id=mapping[key],
                                        description="radiopy.github.io | " + metadata["description"],
                                        name=metadata["name"])


def refresh_songs(mapping=None):
    """
    Refresh songs for all playlists.
    :return:
    """
    if mapping is None:
        # TODO: make sure that mapping doesn't expire
        mapping = json.loads(redis.get("mapping") or "{}")
    for key in mapping:
        queue = redis.redis.lrange(f"{key}:queue", 0, -1)
        length = len(queue)
        # remove duplicates using set
        queue = list(set(queue))
        logger.info(f"refreshing {len(queue)} songs for {key}")
        # add first 100 songs to playlist in one go (Spotify limits this to 100)
        spotify.playlist_replace_items(mapping[key], queue[:100])
        # add remaining songs from queue in chunks of 100
        for index in range(100, len(queue), 100):
            spotify.playlist_add_items(mapping[key], queue[index:index + 100])

        # delete processed songs from queue
        redis.redis.ltrim(f"{key}:queue", length, -1)


if __name__ == "__main__":
    logger.info("delete playlists")
    remaining_mapping = delete_playlists()
    logger.info("create playlists")
    create_playlists(remaining_mapping)
    logger.info("refresh metadata")
    refresh_metadata(remaining_mapping)
    logger.info("refresh songs")
    refresh_songs(remaining_mapping)
