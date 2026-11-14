
from pathlib import Path
from datetime import datetime

import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import (
    ExplicitVRLittleEndian,
    SecondaryCaptureImageStorage,
    generate_uid,
)

from canonical.models import Patient, Procedure, SourceRecord

DATA_DIR = Path(__file__).parent / "data"


def create_sample():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    path = DATA_DIR / "synthetic_study.dcm"

    ds = FileDataset(
        str(path), {}, file_meta=file_meta, preamble=b"\0" * 128
    )

    ds.is_little_endian = True
    ds.is_implicit_VR = False

    ds.SOPClassUID = SecondaryCaptureImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()

    ds.PatientID = "DICOM001"
    ds.PatientName = "SYNTHETIC^PATIENT"
    ds.PatientBirthDate = "19900512"
    ds.PatientSex = "M"

    ds.StudyDate = "20260110"
    ds.Modality = "CT"
    ds.StudyDescription = "Synthetic Chest Imaging Study"
    ds.AccessionNumber = "ACC001"
    ds.Manufacturer = "MedBridge Synthetic Generator"

    ds.save_as(path, enforce_file_format=True)


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y%m%d").date()
    except ValueError:
        return None


def fetch_dicom_data(directory=DATA_DIR):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    files = list(directory.glob("*.dcm"))
    if not files:
        create_sample()
        files = list(directory.glob("*.dcm"))

    patients = {}
    records = []

    for path in files:
        try:
            ds = pydicom.dcmread(path)

            patient_id = str(getattr(ds, "PatientID", "")).strip()
            if not patient_id:
                continue

            patient_name = str(
                getattr(ds, "PatientName", "")
            ).replace("^", " ").strip()

            sex = str(getattr(ds, "PatientSex", "")).upper()
            gender = (
                "male" if sex == "M"
                else "female" if sex == "F"
                else "unknown"
            )

            patient = patients.get(patient_id)

            if patient is None:
                patient = Patient(
                    id=patient_id,
                    name=patient_name or None,
                    birth_date=parse_date(
                        getattr(ds, "PatientBirthDate", "")
                    ),
                    gender=gender,
                    sources=["DICOM"],
                )
                patients[patient_id] = patient

            procedure = Procedure(
                id=str(getattr(ds, "SOPInstanceUID", path.name)),
                name=str(
                    getattr(ds, "StudyDescription", "Imaging Study")
                ),
                procedure_type=str(
                    getattr(ds, "Modality", "unknown")
                ),
                date=parse_date(getattr(ds, "StudyDate", "")),
                status="unknown",
                notes=f"Accession: {getattr(ds, 'AccessionNumber', '')}",
                source="DICOM",
            )

            patient.procedures.append(procedure)

            records.append(
                SourceRecord(
                    source="DICOM",
                    original={
                        "PatientID": patient_id,
                        "PatientName": str(
                            getattr(ds, "PatientName", "")
                        ),
                        "PatientBirthDate": str(
                            getattr(ds, "PatientBirthDate", "")
                        ),
                        "PatientSex": sex,
                        "StudyDate": str(
                            getattr(ds, "StudyDate", "")
                        ),
                        "Modality": str(
                            getattr(ds, "Modality", "")
                        ),
                        "StudyDescription": str(
                            getattr(ds, "StudyDescription", "")
                        ),
                    },
                    mapped={
                        "patient_id": patient.id,
                        "procedure": procedure.model_dump(mode="json"),
                    },
                    normalized={
                        "patient_id": patient.id,
                        "modality": procedure.procedure_type,
                    },
                )
            )

        except Exception as error:
            print(f"FILE ERROR: {path.name}: {error}")

    return list(patients.values()), records


if __name__ == "__main__":
    patients, records = fetch_dicom_data()

    print("DICOM CONNECTOR TEST")
    print("FILES:", len(list(DATA_DIR.glob("*.dcm"))))
    print("PATIENTS:", len(patients))
    print(
        "IMAGING STUDIES:",
        sum(len(p.procedures) for p in patients)
    )
    print("SOURCE RECORDS:", len(records))
    print(
        "ERRORS:",
        sum(len(r.errors) for r in records)
    )
