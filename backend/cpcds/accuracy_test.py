
import csv
from pathlib import Path
from cpcds.connector import fetch_cpcds_data, DATA_DIR


def read_csv(name):
    with (Path(DATA_DIR) / name).open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        return list(csv.DictReader(f))


patients, records = fetch_cpcds_data()

members = read_csv("member.csv")
claims = read_csv("medical_claim.csv")
lines = read_csv("medical_claim_line.csv")
pharmacy = read_csv("pharmacy_claim.csv")

matched = 0
total = 0


def check(label, source, mapped):
    global matched, total
    total += 1
    if str(source).strip() == str(mapped).strip():
        matched += 1
    else:
        print(f"MISMATCH: {label} | SOURCE={source} | MAPPED={mapped}")


print("===== CPCDS ACCURACY AUDIT =====")

# Patient
for row in members:
    p = next((x for x in patients if x.id == row["member_id"]), None)
    if not p:
        print("MISSING PATIENT:", row["member_id"])
        continue

    check("Patient ID", row["member_id"], p.id)
    check(
        "Patient Name",
        f'{row["first_name"]} {row["last_name"]}'.strip(),
        p.name
    )
    check("Birth Date", row["birth_date"], p.birth_date)
    gender = {"M": "male", "F": "female"}.get(
        row["gender"].upper(), "unknown"
    )
    check("Gender", gender, p.gender)

# Diagnosis and Encounter
for row in claims:
    p = next((x for x in patients if x.id == row["member_id"]), None)
    if not p:
        continue

    d = next((x for x in p.diagnoses if x.id == row["claim_id"]), None)
    e = next((x for x in p.encounters if x.id == row["claim_id"]), None)

    if d:
        check("Diagnosis", row["diagnosis"], d.description)
    if e:
        check("Encounter Type", row["claim_type"], e.encounter_type)
        check("Encounter Date", row["service_date"], e.date)

# Procedures
for row in lines:
    claim = next(
        (x for x in claims if x["claim_id"] == row["claim_id"]), None
    )
    if not claim:
        continue

    p = next((x for x in patients if x.id == claim["member_id"]), None)
    procedure = next(
        (x for x in p.procedures if x.id == row["line_id"]), None
    ) if p else None

    if procedure:
        check("Procedure Name", row["description"], procedure.name)
        check("Procedure Code", row["procedure_code"], procedure.procedure_type)

# Medications
for row in pharmacy:
    p = next((x for x in patients if x.id == row["member_id"]), None)
    medication = next(
        (x for x in p.medications if x.id == row["claim_id"]), None
    ) if p else None

    if medication:
        check("Medication Name", row["drug_name"], medication.name)
        check("Medication Quantity", row["quantity"], medication.dose)

accuracy = (matched / total * 100) if total else 0

print(f"FIELDS MATCHED: {matched}/{total}")
print(f"ACCURACY: {accuracy:.2f}%")
print("SOURCE RECORD ERRORS:", len([
    r for r in records if r.errors
]))
