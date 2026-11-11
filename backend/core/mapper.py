
def map_record(record: dict, mapping: dict) -> dict:
    field_rules = mapping["fields"]
    result = {}

    for original_field, canonical_field in field_rules.items():
        if original_field in record:
            result[canonical_field] = record[original_field]

    return result
