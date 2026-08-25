"""Export every collection in the target database to one JSON file each.

Documents are written as MongoDB Relaxed Extended JSON so that types like
ObjectId and datetime survive the round trip.

Connection settings come from the environment:

    MONGO_HOST      (default: localhost)
    MONGO_PORT      (default: 27017)
    MONGO_DATABASE  (required)
    MONGO_USERNAME  (required)
    MONGO_PASSWORD  (required)
    MONGO_AUTH_DB   (default: admin)

Example:

    MONGO_DATABASE=mydb MONGO_USERNAME=myuser MONGO_PASSWORD=secret \\
        uv run python export_mongo.py
"""

import os
import pathlib
import sys

from bson.json_util import JSONOptions, dumps
from pymongo import MongoClient

OUT_DIR = pathlib.Path(__file__).parent / "export"
BATCH = 1000

json_opts = JSONOptions(json_mode=2)  # RELAXED


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        sys.exit(f"error: environment variable {name} is required")
    return value


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    client = MongoClient(
        host=env("MONGO_HOST", "localhost"),
        port=int(env("MONGO_PORT", "27017")),
        username=env("MONGO_USERNAME"),
        password=env("MONGO_PASSWORD"),
        authSource=env("MONGO_AUTH_DB", "admin"),
        serverSelectionTimeoutMS=10000,
    )
    db = client[env("MONGO_DATABASE")]

    for name in sorted(db.list_collection_names()):
        path = OUT_DIR / f"{name}.json"
        count = 0
        with path.open("w", encoding="utf-8") as fh:
            fh.write("[\n")
            cursor = db[name].find({}, batch_size=BATCH)
            for doc in cursor:
                if count:
                    fh.write(",\n")
                fh.write(dumps(doc, json_options=json_opts, ensure_ascii=False))
                count += 1
            fh.write("\n]\n")
        size_mb = path.stat().st_size / 1024 / 1024
        print(f"{name:24} {count:>7} docs  {size_mb:>8.2f} MB", flush=True)

    client.close()


if __name__ == "__main__":
    main()
