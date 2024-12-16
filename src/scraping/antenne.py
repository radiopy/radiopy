import argparse
import datetime
import json

import requests

from src.log_setup import logging
from src.redis_manager import RedisManager

logger = logging.getLogger(__name__)
redis = RedisManager("scraping:antenne")
session = requests.Session()


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
    response = session.get("https://www.antenne.de/api/channels").json()
    for channel in response["data"]:
        data = {
            "type": "playlist",
            "name": channel["title"] + (" | Antenne Bayern" if "Antenne" not in channel["title"].lower() else ""),
            "description": channel["description"],
            "url": channel["website"],
            "last_run": datetime.datetime.now(datetime.UTC).timestamp()
        }
        if channel["logo"]:
            data["image"] = channel["logo"][0]["url"]
        redis.set(f"{channel['stream']['mountpoint']}:metadata", json.dumps(data))

def get_songs():
    logger.info("Scraping songs...")
    response = session.get("https://www.antenne.de/api/metadata/now").json()
    for channel in response["data"]:
        if channel["class"] != "Music":
            continue
        song = {
            "airtime": channel["starttime"],
            "id": channel["masterid"],
            "title": channel["title"],
            "artists": channel["artist"]
        }
        redis.rpush(f"{channel['mountpoint']}:songs", json.dumps(song))
        redis.set(f"{channel['mountpoint']}:updated", datetime.datetime.now(datetime.UTC).timestamp())

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
