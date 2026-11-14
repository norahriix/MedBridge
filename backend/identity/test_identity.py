
from datetime import date

from canonical.models import Patient
from identity.matcher import match_patients


def make_patient(pid, name, national_id, birth_date):
    return Patient(
        id=pid,
        name=name,
        national_id=national_id,
        birth_date=birth_date,
        gender="female",
        sources=["synthetic_test"]
    )


patients = [
    make_patient("P1", "Sara Test", "1001", date(1990, 1, 1)),
    make_patient("P2", "Sara Test", "1001", date(1990, 1, 1)),
    make_patient("P3", "Omar Test", "1002", date(1985, 2, 2)),
    make_patient("P4", "Omar Test", "1003", date(1985, 2, 2)),
    make_patient("P5", "Lina Test", None, date(1992, 3, 3)),
    make_patient("P6", "Lina Test", None, date(1992, 3, 3)),
]

# Ground truth: pairs that truly represent the same patient
actual_matches = {
    frozenset(("P1", "P2")),
    frozenset(("P5", "P6")),
}

results = match_patients(patients)

predicted_matches = {
    frozenset((result.patient_a_id, result.patient_b_id))
    for result in results
   if result.status in ("MATCH", "POSSIBLE_MATCH")
}

true_positive = len(actual_matches & predicted_matches)
false_positive = len(predicted_matches - actual_matches)
false_negative = len(actual_matches - predicted_matches)

precision = (
    true_positive / (true_positive + false_positive)
    if true_positive + false_positive else 0
)

recall = (
    true_positive / (true_positive + false_negative)
    if true_positive + false_negative else 0
)

f1 = (
    2 * precision * recall / (precision + recall)
    if precision + recall else 0
)

print("\n===== IDENTITY MATCHING AUDIT =====")
print("TOTAL PAIRS:", len(results))
print("TRUE POSITIVES:", true_positive)
print("FALSE POSITIVES:", false_positive)
print("FALSE NEGATIVES:", false_negative)
print(f"PRECISION: {precision * 100:.2f}%")
print(f"RECALL: {recall * 100:.2f}%")
print(f"F1 SCORE: {f1 * 100:.2f}%")
