
from normalization.dates import normalize_date
from normalization.demographics import normalize_gender
from normalization.units import normalize_weight
from normalization.normalizer import normalize


def test_date():
    assert normalize_date("10/04/1995", "%d/%m/%Y") == "1995-04-10"


def test_gender():
    rules = {"female": ["F", "Female"]}
    assert normalize_gender("F", rules) == "female"


def test_weight():
    assert normalize_weight(70000, "g") == (70.0, "kg")


def test_original_data():
    original = {"gender": "F", "birth_date": "1995-04-10"}
    result = normalize(original)

    assert original["gender"] == "F"
    assert result["gender"] == "female"
