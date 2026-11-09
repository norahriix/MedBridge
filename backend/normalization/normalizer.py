
from pathlib import Path
import yaml

from normalization.dates import normalize_date
from normalization.demographics import normalize_gender


ROOT = Path(__file__).resolve().parents[2]


def normalize(record: dict) -> dict:
    result = record.copy()

    if result.get("birth_date"):
        result["birth_date"] = normalize_date(
            str(result["birth_date"]),
            "%Y-%m-%d"
        )

    if result.get("gender"):
        rules_path = ROOT / "config/terminology/gender.yaml"

        with rules_path.open("r", encoding="utf-8") as file:
            rules = yaml.safe_load(file)

        result["gender"] = normalize_gender(
            str(result["gender"]),
            rules
        )

    return result
