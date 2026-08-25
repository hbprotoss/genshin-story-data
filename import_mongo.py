"""Import JSON files from the export directory back into MongoDB.

Reads the MongoDB Relaxed Extended JSON files produced by ``export_mongo.py``
and inserts the documents into the target database, restoring BSON types such
as ObjectId and datetime.

Connection settings come from the environment:

    MONGO_HOST      (default: localhost)
    MONGO_PORT      (default: 27017)
    MONGO_DATABASE  (required)
    MONGO_USERNAME  (required)
    MONGO_PASSWORD  (required)
    MONGO_AUTH_DB   (default: admin)

By default a non-empty target collection is left untouched and reported as
skipped; pass --drop to replace its contents.

Example:

    MONGO_DATABASE=mydb MONGO_USERNAME=myuser MONGO_PASSWORD=secret \\
        uv run python import_mongo.py --drop
"""

import argparse
import os
import pathlib
import sys

from bson.json_util import JSONOptions, loads
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

IN_DIR = pathlib.Path(__file__).parent / "export"
BATCH = 1000

# Must match the export side so $oid / $date markers are decoded back to
# ObjectId and datetime rather than left as plain dicts.
json_opts = JSONOptions(json_mode=2)  # RELAXED


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        sys.exit(f"error: environment variable {name} is required")
    return value


def batched(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--drop",
        action="store_true",
        help="delete existing documents in a collection before importing",
    )
    p.add_argument(
        "--only",
        metavar="NAME",
        nargs="+",
        help="import only these collections (default: all files in export/)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would happen without writing anything",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    files = sorted(IN_DIR.glob("*.json"))
    if args.only:
        wanted = set(args.only)
        files = [f for f in files if f.stem in wanted]
        missing = wanted - {f.stem for f in files}
        if missing:
            sys.exit(f"error: no export file for: {', '.join(sorted(missing))}")
    if not files:
        sys.exit(f"error: no JSON files found in {IN_DIR}")

    client = MongoClient(
        host=env("MONGO_HOST", "localhost"),
        port=int(env("MONGO_PORT", "27017")),
        username=env("MONGO_USERNAME"),
        password=env("MONGO_PASSWORD"),
        authSource=env("MONGO_AUTH_DB", "admin"),
        serverSelectionTimeoutMS=10000,
    )
    db = client[env("MONGO_DATABASE")]

    imported = skipped = failed = 0

    for path in files:
        name = path.stem
        docs = loads(path.read_text(encoding="utf-8"), json_options=json_opts)

        if not docs:
            print(f"{name:24} {'-':>7}       empty file, nothing to import")
            continue

        existing = db[name].count_documents({})
        if existing and not args.drop:
            print(f"{name:24} {'-':>7}       SKIPPED, {existing} docs present (use --drop)")
            skipped += 1
            continue

        if args.dry_run:
            action = f"would replace {existing} docs" if existing else "would insert"
            print(f"{name:24} {len(docs):>7} docs  {action}")
            continue

        if existing:
            db[name].delete_many({})

        try:
            count = 0
            for batch in batched(docs, BATCH):
                count += len(db[name].insert_many(batch, ordered=False).inserted_ids)
            print(f"{name:24} {count:>7} docs  imported")
            imported += 1
        except BulkWriteError as exc:
            errs = exc.details.get("writeErrors", [])
            print(
                f"{name:24} {exc.details.get('nInserted', 0):>7} docs  "
                f"FAILED, {len(errs)} write errors; first: {errs[0]['errmsg'][:120]}"
            )
            failed += 1

    client.close()

    summary = f"{imported} collections imported"
    if skipped:
        summary += f", {skipped} skipped"
    if failed:
        summary += f", {failed} with errors"
    print(f"\n{summary}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
