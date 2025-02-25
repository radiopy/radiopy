import ftplib
import json
from io import BytesIO

from src.config import config
from src.redis_manager import RedisManager

config = config.get("ftp")

redis = RedisManager()


def get_all_metadata():
    keys = redis.get_keys("metadata")
    result = {}
    for key in keys:
        metadata = redis.get(key, auto_extend=False)
        if metadata:
            result[key] = json.loads(metadata)
    return result


def add_playlist_mapping(metadata):
    mapping = json.loads(redis.get("mapping") or "{}")
    for key, value in mapping.items():
        metadata[key + ":metadata"]["playlist"] = value
    return metadata


def resolve_references(metadata):
    repeat = True
    max_repeats = 100
    while repeat:
        repeat = False
        for key, value in metadata.items():
            if "reference" in value:
                reference: dict = metadata[value["reference"] + ":metadata"].copy()
                del value["reference"]
                reference.update(value)
                metadata[key] = reference
                if "reference" in reference:
                    repeat = True
        max_repeats -= 1
        if max_repeats <= 0:
            raise RecursionError("Max repeats reached")

    for key, value in metadata.copy().items():
        if value.get("invisible"):
            del metadata[key]
        elif "invisible" in value:
            del value["invisible"]

    return metadata


def categorize_metadata(metadata):
    result = {}
    all_items = []
    # sort by key length
    keys = sorted(metadata.keys(), key=lambda x: len(x))
    for key in keys:
        new_key = key[:-9]  # remove ":metadata" suffix
        prefixes = new_key.split(":")
        prefix = None
        parent = result
        for part in prefixes:
            if prefix is None:
                prefix = part
            else:
                prefix += ":" + part
            if prefix in parent:
                parent = parent[prefix]["children"]
        metadata[key]["children"] = {}
        parent[new_key] = metadata[key]
        all_items.append(metadata[key])

    # convert children dictionaries to lists
    for item in all_items:
        if item["children"]:
            children = item["children"]
            item["children"] = list(children.values())
        else:
            del item["children"]
    return result


def main():
    metadata = get_all_metadata()
    metadata = add_playlist_mapping(metadata)
    metadata = resolve_references(metadata)
    metadata = categorize_metadata(metadata)
    metadata = list(metadata.values())
    if config:
        with ftplib.FTP_TLS(config["hostname"], config["username"], config["password"]) as session:
            session.prot_p()
            session.storbinary("STOR metadata.json",
                               BytesIO(json.dumps(metadata, separators=(",", ":"), ensure_ascii=False).encode("utf-8")))
    else:
        print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
