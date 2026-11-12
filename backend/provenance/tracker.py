from canonical.models import Provenance


def track_provenance(
    source: str,
    original_field: str,
    original_value,
    transformations: list[str]
) -> Provenance:

    return Provenance(
        source=source,
        original_field=original_field,
        original_value=str(original_value),
        transformations=transformations
    )