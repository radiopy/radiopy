import requests
import json
import datetime

from src.redis_manager import RedisManager

BASE_URL = "https://www.bigfm.de/api"

redis = RedisManager("scraping:bigfm")
session = requests.Session()


def scrape_channels():
    response = session.get(f"{BASE_URL}/webradio/uebersicht-bigfm").json()

    sections = [section for section in response["sections"] if section["type"] == "teaser"]
    channels = {channel["path"]["alias"]: channel for section in sections for channel in section["teasers"]}
    for index, path in enumerate(channels):
        print(index + 1, "/", len(channels), end="\r")
        ch_response = session.get(f"{BASE_URL}/{path}").json()
        for section in ch_response["sections"]:
            if "stream" not in section or section["type"] != "stream":
                continue
            channels[path]["streamId"] = int(section["stream"]["stream"])
    print()

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
               "guid": song["song"]["entry"][0]["guid"],
               "title": song["song"]["entry"][0]["title"],
               "artists": " ".join([artist["name"] for artist in song["song"]["entry"][0]["artist"]["entry"]])}
              for song in response["result"]["entry"]]
    return result


def set_redis(data):
    metadata = {
        "name": "BigFM",
        "description": "Deutschlands biggste Beats",
        "url": "https://www.bigfm.de/",
        "image": "https://file.atsw.de/production/static/1729071412751/ab66799083e298839f274a7a8dd9fa15.svg",
        "last_run": datetime.datetime.now(datetime.UTC).timestamp()  # make sure it's UTC
    }
    redis.set(f"metadata", json.dumps(metadata))
    for section, channels in data.items():
        redis.set(f"{section[0]}:metadata", json.dumps({
            "title": section[1],
            "last_run": datetime.datetime.now(datetime.UTC).timestamp()
        }))
        for path, channel in channels.items():
            redis.set(f"{section[0]}:{path}:metadata", json.dumps({
                "name": channel["title"],
                "description": channel["intro"]["text"]["value"].strip(),
                "url": f"https://www.bigfm.de/{path}",
                "image": channel["intro"]["image"]["image"]["uri"]["url"],
                "last_run": datetime.datetime.now(datetime.UTC).timestamp()
            }))
            redis_path = f"{section[0]}:{path}"
            today = datetime.datetime.now(datetime.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            songs = get_songs(channel["streamId"], today - datetime.timedelta(hours=24), today)
            redis.rpush(f"{redis_path}:songs", *[json.dumps(song) for song in songs])
            redis.set(f"{redis_path}:updated", datetime.datetime.now(datetime.UTC).timestamp())
        redis.set(f"{section[0]}:updated", datetime.datetime.now(datetime.UTC).timestamp())
    redis.set(f"updated", datetime.datetime.now(datetime.UTC).timestamp())


if __name__ == "__main__":
    print(set_redis(scrape_channels()))
