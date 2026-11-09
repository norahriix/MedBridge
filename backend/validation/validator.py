from datetime import datetime


def validate_required_fields(record: dict) -> list[str]:
    errors = []

    required_fields = [
        "source_patient_id",
        "name",
        "birth_date",
        "gender",
    ]

    for field in required_fields:
        if not record.get(field):
            errors.append(f"Missing required field: {field}")

    return errors


def validate_birth_date(birth_date: str) -> list[str]:
    errors = []

    try:
        datetime.strptime(birth_date, "%Y-%m-%d")
    except ValueError:
        errors.append("Invalid birth_date format")

    return errors


def validate_patient(record: dict) -> list[str]:
    errors = []

    errors.extend(validate_required_fields(record))

    if record.get("birth_date"):
        errors.extend(validate_birth_date(record["birth_date"]))

    return errors