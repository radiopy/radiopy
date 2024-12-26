import argparse
import datetime
import json

import requests

from src.log_setup import logging
from src.redis_manager import RedisManager

logger = logging.getLogger(__name__)
redis = RedisManager("scraping:antenne")
session = requests.Session()

STATIONS = [
    {
        "name": "ANTENNE BAYERN",
        "description": "Bayerns bester Musikmix",
        "url": "https://antenne.de",
        "image": "https://www.antenne.de/logos/station-antenne-bayern/station.svg"
    },
    {
        "name": "ROCK ANTENNE",
        "url": "https://rockantenne.de",
        "image": "https://www.rockantenne.de/logos/station-rock-antenne/station.svg"
    },
    {
        "name": "ROCK ANTENNE Bayern",
        "url": "https://rockantenne.bayern",
        "image": "https://www.rockantenne.bayern/logos/station-rock-antenne-bayern/station.svg"
    },
    {
        "name": "ROCK ANTENNE Hamburg",
        "url": "https://rockantenne.hamburg",
        "image": "https://www.rockantenne.hamburg/logos/station-rock-antenne-hamburg/station.svg"
    },
    {
        "name": "ROCK ANTENNE Österreich",
        "url": "https://rockantenne.at",
        "image": "https://www.rockantenne.at/logos/station-rock-antenne-at/station.svg"
    },
    {
        "name": "ANTENNE NRW",
        "url": "https://antenne.nrw",
        "image": "https://www.antenne.nrw/logos/station-antenne-nrw/station.svg"
    },
    {
        "name": "OLDIE ANTENNE",
        "url": "https://oldie-antenne.de",
        "image": "https://www.oldie-antenne.de/logos/station-oldie-antenne/station.svg"
    }
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--metadata", help="Flag to get the metadata", action="store_true")
    parser.add_argument("-s", "--songs", help="Flag to get the current songs", action="store_true")
    return parser.parse_args()


def get_metadata():
    logger.info("Scraping metadata...")
    metadata = {
        "type": "category",
        "name": "Antenne Bayern",
        "description": "Bayerns bester Musikmix",
        "url": "https://antenne.de",
        "image": "https://www.antenne.de/logos/station-antenne-bayern/station.svg",
        "last_run": datetime.datetime.now(datetime.UTC).timestamp()  # make sure it's UTC
    }
    redis.set("metadata", json.dumps(metadata))

    # reverse order to have the more popular ones at the top (some stations get overwritten)
    for station in STATIONS[::-1]:
        response = session.get(f"{station['url']}/api/channels").json()
        for channel in response["data"]:
            data = {
                "type": "playlist",
                "name": channel["title"] + (f" | {station['name']}"
                                            if "antenne" not in channel["title"].lower() else ""),
                "description": channel["description"],
                "url": channel["website"],
                "last_run": datetime.datetime.now(datetime.UTC).timestamp(),
                "invisible": True
            }
            if channel["logo"]:
                data["image"] = channel["logo"][0]["url"]
            path = f"channels:{channel['stream']['mountpoint']}"
            redis.set(f"{path}:metadata", json.dumps(data))

            data = {
                "reference": f"{redis.prefix}{path}",
                "name": channel["title"],
                "description": channel["description"],
                "url": channel["website"],
                "invisible": False
            }
            redis.set(f"metadata:{station['name']}:{channel['stream']['mountpoint']}:metadata", json.dumps(data))


def get_songs():
    logger.info("Scraping songs...")
    mountpoints = []
    for station in STATIONS:
        response = session.get(f"{station['url']}/api/metadata/now").json()
        for channel in response["data"]:
            if channel["class"] != "Music" or channel["mountpoint"] in mountpoints:
                continue
            mountpoints.append(channel["mountpoint"])
            song = {
                "airtime": channel["starttime"],
                "id": channel["masterid"],
                "title": channel["title"],
                "artists": channel["artist"]
            }
            redis.rpush(f"channels:{channel['mountpoint']}:songs", json.dumps(song))
            redis.set(f"channels:{channel['mountpoint']}:updated",
                      datetime.datetime.now(datetime.UTC).timestamp())


if __name__ == "__main__":
    args = parse_args()
    if args.metadata:
        get_metadata()
    if args.songs:
        get_songs()
    if not args.metadata and not args.songs:
        # run both if no flags are set
        get_metadata()
        get_songs()
