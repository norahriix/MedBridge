
from pathlib import Path
import pytest

from ingestion.readers import read_source


ROOT = Path(__file__).resolve().parents[2]


def test_read_hospital_a():
    path = ROOT / "data/hospital_a/patients.json"

    records = read_source(str(path))

    assert len(records) == 2
    assert records[0]["patient_id"] == "A100"
    assert records[0]["patient_name"] == "Sara Ahmed"


def test_read_hospital_b():
    path = ROOT / "data/hospital_b/patients.json"

    records = read_source(str(path))

    assert len(records) == 2
    assert records[0]["record_no"] == "B200"
    assert records[0]["fullName"] == "Sara Ahmed"


def test_reject_unsupported_file():
    with pytest.raises(ValueError):
        read_source("patients.txt")

def test_read_hospital_c_csv():
    path = ROOT / "data/hospital_c/patients.csv"

    records = read_source(str(path))

    assert len(records) == 2
    assert records[0]["patient_code"] == "C300"
    assert records[0]["patient_full_name"] == "Sara Ahmed"
