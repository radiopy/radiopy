# check if user is already logged in.
# if so, name the username and ID and ask if they want to choose a different user or log out.
# if not, try to log in.

import spotipy
from spotipy import SpotifyOAuth
from src.config import config
from src.log_setup import logging
from src.redis_manager import RedisManager

redis = RedisManager()

logger = logging.getLogger(__name__)

spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**config["spotify"],
                                                    cache_handler=spotipy.RedisCacheHandler(redis.redis),
                                                    open_browser=False))

while True:
    user = spotify.me()
    print(f"Logged in as {user['display_name']} ({user['id']})")
    choice = input("Do you want to log in as a different user? [y/N] ")
    if choice.lower() == "y":
        redis.redis.delete(spotify.auth_manager.cache_handler.key)
    else:
        break
