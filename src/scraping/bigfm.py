import datetime
import json

import requests

from src.log_setup import logging
from src.redis_manager import RedisManager

BASE_URL = "https://www.bigfm.de/api"

logger = logging.getLogger(__name__)
redis = RedisManager("scraping:bigfm")
session = requests.Session()


def scrape_channels():
    logger.info("Scraping metadata...")
    response = session.get(f"{BASE_URL}/webradio/uebersicht-bigfm").json()

    sections = [section for section in response["sections"] if section["type"] == "teaser"]
    channels = {channel["path"]["alias"]: channel for section in sections for channel in section["teasers"]}
    for index, path in enumerate(channels):
        logger.info(f"{index + 1:02d}/{len(channels)}: {path}")
        ch_response = session.get(f"{BASE_URL}/{path}").json()
        for section in ch_response["sections"]:
            if "stream" not in section or section["type"] != "stream":
                continue
            channels[path]["streamId"] = int(section["stream"]["stream"])

    result = {}
    for section in sections:
        result[(section["id"], section["title"])] = {}
        for channel in section["teasers"]:
            path = channel["path"]["alias"]
            if path in channels:
                result[(section["id"], section["title"])][path] = channels[path]
    return result


def beautify_output(sections):
    result = ""
    for section, channels in sections.items():
        result += f"{section}\n"
        result += "-" * 25 + "\n"
        for path, channel in channels.items():
            result += f"{channel['title']} [{channel['streamId']}]:\n"
            result += f" INF: {channel['intro']['text']['value'].strip()}\n"
            result += f" IMG: {channel['intro']['image']['image']['uri']['url']}\n\n"
        result += "\n\n"
    return result


def get_songs(station: int, start: datetime.datetime, end: datetime.datetime = None):
    response = session.get("https://asw.api.iris.radiorepo.io/v2/playlist/search.json",
                           params={"station": station, "start": start, "end": end}).json()
    result = [{"airtime": song["airtime"],
               "duration": song["duration"],
               "id": song["song"]["entry"][0]["guid"],
               "title": song["song"]["entry"][0]["title"],
               "artists": " ".join([artist["name"] for artist in song["song"]["entry"][0]["artist"]["entry"]])}
              for song in response["result"].get("entry", [])]
    return result


def collect_channels(channels: dict):
    logger.info("Collecting channel songs...")
    for index, item in enumerate(channels.items()):
        path, channel = item
        logger.info(f"{index + 1:02d}/{len(channels)}: {path}")
        redis.set(f"channels:{path}:metadata", json.dumps({
            "type": "playlist",
            "name": channel["title"] + (" | bigFM" if "bigfm" not in channel["title"].lower() else ""),
            "description": channel["intro"]["text"]["value"].strip(),
            "url": f"https://www.bigfm.de{path}",
            "image": channel["intro"]["image"]["image"]["uri"]["url"],
            "last_run": datetime.datetime.now(datetime.UTC).timestamp(),
            "invisible": True
        }))
        today = datetime.datetime.now(datetime.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        songs = get_songs(channel["streamId"], today - datetime.timedelta(hours=24), today)
        if songs:
            redis.rpush(f"channels:{path}:songs", *[json.dumps(song) for song in songs])
        redis.set(f"channels:{path}:updated", datetime.datetime.now(datetime.UTC).timestamp())


def add_metadata(data):
    metadata = {
        "type": "category",
        "name": "bigFM",
        "description": "Deutschlands biggste Beats",
        "url": "https://www.bigfm.de/",
        "image": "https://file.atsw.de/production/static/1729071412751/ab66799083e298839f274a7a8dd9fa15.svg",
        "last_run": datetime.datetime.now(datetime.UTC).timestamp()  # make sure it's UTC
    }
    redis.set(f"metadata", json.dumps(metadata))
    for section, channels in data.items():
        key = "metadata"
        # if category has no name, put the channels into the main category
        if section[1] is not None:
            key = f"{key}:{section[0]}"
            redis.set(f"{key}:metadata", json.dumps({
                "type": "category",
                "name": section[1],
                "last_run": datetime.datetime.now(datetime.UTC).timestamp()
            }))
        for path, channel in channels.items():
            redis.set(f"{key}:{path}:metadata", json.dumps({
                "reference": f"{redis.prefix}channels:{path}",
                "name": channel["title"],  # use default name
                "invisible": False
            }))


def main():
    data = scrape_channels()
    all_channels = {}
    for channels in data.values():
        all_channels.update(channels)
    collect_channels(all_channels)
    add_metadata(data)


if __name__ == "__main__":
    main()
