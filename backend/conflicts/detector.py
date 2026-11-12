
from collections import defaultdict


def _get_value(item, key):
    """Read a field from either a dictionary or an object."""
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def detect_conflicts(observations):
    """
    Detect conflicting medical observations.

    Observations with the same type, date and unit
    are compared across different sources.

    The function flags disagreements for human review.
    It does not decide which medical value is correct.
    """

    grouped = defaultdict(list)

    for observation in observations:
        obs_type = _get_value(observation, "type")
        value = _get_value(observation, "value")
        unit = _get_value(observation, "unit")
        date = _get_value(observation, "date")
        source = _get_value(observation, "source")

        if None in (obs_type, value, unit, date):
            continue

        key = (obs_type, date, unit)

        grouped[key].append({
            "value": value,
            "source": source
        })

    conflicts = []

    for (obs_type, date, unit), items in grouped.items():

        unique_values = set(item["value"] for item in items)

        if len(unique_values) > 1:

            conflicts.append({
                "type": obs_type,
                "date": date,
                "unit": unit,
                "values": [
                    {
                        "value": item["value"],
                        "source": item["source"]
                    }
                    for item in items
                ],
                "severity": "critical",
                "status": "review_required",
                "message": (
                    "Conflicting medical observations "
                    "were found. Human review is required."
                )
            })

    return conflicts


def has_critical_conflict(observations):
    """Check whether any conflicting observations exist."""

    conflicts = detect_conflicts(observations)

    return any(
        conflict["severity"] == "critical"
        for conflict in conflicts
    )