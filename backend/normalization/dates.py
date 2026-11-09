
from datetime import datetime

def normalize_date(value: str, fmt: str) -> str:
    parsed = datetime.strptime(value.strip(), fmt)
    return parsed.strftime("%Y-%m-%d")
