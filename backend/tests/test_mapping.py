
from pathlib import Path
import yaml

from ingestion.readers import read_source
from core.mapper import map_record


ROOT = Path(__file__).resolve().parents[2]


def test_hospital_a_mapping():
    records = read_source(
        str(ROOT / "data/hospital_a/patients.json")
    )

    with open(
        ROOT / "mappings/hospital_a/mapping.yaml",
        encoding="utf-8"
    ) as file:
        mapping = yaml.safe_load(file)

    result = map_record(records[0], mapping)

    assert result["name"] == "Sara Ahmed"
    assert result["birth_date"] == "1995-04-10"
    assert result["source_patient_id"] == "A100"
    assert result["gender"] == "F"


def test_hospital_b_mapping():
    records = read_source(
        str(ROOT / "data/hospital_b/patients.json")
    )

    with open(
        ROOT / "mappings/hospital_b/mapping.yaml",
        encoding="utf-8"
    ) as file:
        mapping = yaml.safe_load(file)

    result = map_record(records[0], mapping)

    assert result["name"] == "Sara Ahmed"
    assert result["birth_date"] == "1995-04-10"
    assert result["source_patient_id"] == "B200"
    assert result["gender"] == "Female"

def test_hospital_c_mapping():
    records = read_source(
        str(ROOT / "data/hospital_c/patients.csv")
    )

    with open(
        ROOT / "mappings/hospital_c/mapping.yaml",
        encoding="utf-8"
    ) as file:
        mapping = yaml.safe_load(file)

    result = map_record(records[0], mapping)

    assert result["source_patient_id"] == "C300"
    assert result["name"] == "Sara Ahmed"
    assert result["birth_date"] == "1995-04-10"
    assert result["gender"] == "F"
