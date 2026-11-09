
def normalize_gender(value: str, rules: dict) -> str:
    value = value.strip().lower()

    for gender, variants in rules.items():
        if value == gender.lower():
            return gender

        for variant in variants:
            if value == variant.lower():
                return gender

    return "unknown"
    