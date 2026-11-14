
from bfd_rif.connector import fetch_bfd_data, DATA_DIR, read_table

patients, records = fetch_bfd_data()

beneficiaries = read_table("beneficiary.csv")
claims = read_table("inpatient_claim.csv")
diagnoses = read_table("diagnosis.csv")
prescriptions = read_table("prescription.csv")

matched = 0
total = 0


def check(label, source, mapped):
    global matched, total
    total += 1
    if str(source).strip() == str(mapped).strip():
        matched += 1
    else:
        print(f"MISMATCH: {label} | SOURCE={source} | MAPPED={mapped}")


print("===== BFD RIF ACCURACY AUDIT =====")

for row in beneficiaries:
    patient = next(
        (p for p in patients if p.id == row["BENE_ID"]), None
    )
    if not patient:
        continue

    check("Patient ID", row["BENE_ID"], patient.id)
    check(
        "Birth Date",
        f'{row["BENE_BIRTH_DT"][:4]}-{row["BENE_BIRTH_DT"][4:6]}-{row["BENE_BIRTH_DT"][6:8]}',
        patient.birth_date
    )

    expected_gender = (
        "male" if row["BENE_SEX_IDENT_CD"] == "1"
        else "female" if row["BENE_SEX_IDENT_CD"] == "2"
        else "unknown"
    )
    check("Gender", expected_gender, patient.gender)

for row in claims:
    patient = next(
        (p for p in patients if p.id == row["DESYNPUF_ID"]), None
    )
    encounter = next(
        (e for e in patient.encounters if e.id == row["CLM_ID"]), None
    ) if patient else None

    if encounter:
        check("Claim ID", row["CLM_ID"], encounter.id)
        check("Encounter Type", "inpatient", encounter.encounter_type)
        check(
            "Admission Date",
            f'{row["CLM_ADMSN_DT"][:4]}-{row["CLM_ADMSN_DT"][4:6]}-{row["CLM_ADMSN_DT"][6:8]}',
            encounter.date
        )

for row in diagnoses:
    patient = next(
        (p for p in patients if p.id == row["DESYNPUF_ID"]), None
    )
    diagnosis = next(
        (d for d in patient.diagnoses
         if d.id == f'{row["CLM_ID"]}-{row["ICD9_DGNS_CD"]}'),
        None
    ) if patient else None

    if diagnosis:
        check("Diagnosis Code", row["ICD9_DGNS_CD"], diagnosis.code)

for row in prescriptions:
    patient = next(
        (p for p in patients if p.id == row["DESYNPUF_ID"]), None
    )
    medication = next(
        (m for m in patient.medications if m.id == row["PDE_ID"]),
        None
    ) if patient else None

    if medication:
        check("Medication ID", row["PDE_ID"], medication.id)
        check("Medication Name", row["PROD_SRVC_ID"], medication.name)

accuracy = matched / total * 100 if total else 0

print(f"FIELDS MATCHED: {matched}/{total}")
print(f"ACCURACY: {accuracy:.2f}%")
print("SOURCE RECORD ERRORS:", sum(len(r.errors) for r in records))
