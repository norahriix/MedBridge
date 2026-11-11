
import csv
import json
from pathlib import Path


def read_source(path: str) -> list[dict]:
    file_path = Path(path)
    extension = file_path.suffix.lower()

    if extension == ".json":
        with file_path.open("r", encoding="utf-8") as file:
            records = json.load(file)

    elif extension == ".csv":
        with file_path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            records = list(csv.DictReader(file))

    else:
        raise ValueError(
            f"Unsupported file format: {extension}"
        )

    if not isinstance(records, list):
        raise ValueError("Expected a list of records")

    if not all(isinstance(item, dict) for item in records):
        raise ValueError("Every record must be an object")

    return records

