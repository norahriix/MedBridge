
from pathlib import Path
import pydicom

from dicom.connector import fetch_dicom_data, DATA_DIR

patients, records = fetch_dicom_data()

files = list(Path(DATA_DIR).glob("*.dcm"))

matched = 0
total = 0


def check(label, source, mapped):
    global matched, total
    total += 1

    if str(source).strip() == str(mapped).strip():
        matched += 1
    else:
        print(
            f"MISMATCH: {label} | "
            f"SOURCE={source} | MAPPED={mapped}"
        )


print("===== DICOM ACCURACY AUDIT =====")

for path in files:
    ds = pydicom.dcmread(path)

    patient_id = str(ds.PatientID)
    patient = next(
        (p for p in patients if p.id == patient_id),
        None
    )

    if not patient:
        print("MISSING PATIENT:", patient_id)
        continue

    check("Patient ID", ds.PatientID, patient.id)
    check(
        "Patient Name",
        str(ds.PatientName).replace("^", " ").strip(),
        patient.name
    )

    expected_gender = (
        "male" if str(ds.PatientSex).upper() == "M"
        else "female" if str(ds.PatientSex).upper() == "F"
        else "unknown"
    )
    check("Patient Gender", expected_gender, patient.gender)

    check(
        "Birth Date",
        f"{ds.PatientBirthDate[:4]}-{ds.PatientBirthDate[4:6]}-{ds.PatientBirthDate[6:8]}",
        patient.birth_date
    )

    procedure = next(
        (x for x in patient.procedures
         if x.id == str(ds.SOPInstanceUID)),
        None
    )

    if procedure:
        check("Modality", ds.Modality, procedure.procedure_type)
        check(
            "Study Description",
            ds.StudyDescription,
            procedure.name
        )
        check(
            "Study Date",
            f"{ds.StudyDate[:4]}-{ds.StudyDate[4:6]}-{ds.StudyDate[6:8]}",
            procedure.date
        )

print(f"FIELDS MATCHED: {matched}/{total}")
print(
    f"ACCURACY: {(matched / total * 100) if total else 0:.2f}%"
)
print("SOURCE RECORD ERRORS:", sum(len(r.errors) for r in records))
