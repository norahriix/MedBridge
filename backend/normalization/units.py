
def normalize_weight(value: float, unit: str) -> tuple[float, str]:
    unit = unit.strip().lower()

    if unit == "kg":
        return value, "kg"

    if unit == "g":
        return value / 1000, "kg"

    raise ValueError(f"Unsupported weight unit: {unit}")
