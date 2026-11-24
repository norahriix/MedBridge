# MedBridge

**A Clinical Data Interoperability Platform**

MedBridge is a healthcare data interoperability project designed to collect, normalize, map, and integrate clinical data from multiple hospital systems and healthcare data formats into a unified canonical data model.

The project includes a FastAPI backend, a web-based interface, synthetic hospital datasets, healthcare data connectors, identity matching, and benchmarking tools.

> **Important:** This project uses synthetic test data only. It is intended for development, research, and technical evaluation, not for production clinical use.

## Key Features

- Multi-hospital clinical data integration.
- Canonical data modeling and normalization.
- FHIR R4 integration and conversion.
- Clinical data mapping and transformation.
- Patient identity matching.
- Data conflict detection and review.
- Hospital configuration and source management.
- API-based integration using FastAPI.
- Synthetic data generation and benchmarking.
- Web-based management interface.

## Supported Data Formats and Connectors

| Format | Implementation |
|---|---|
| FHIR R4 | Implemented |
| C-CDA XML | Implemented |
| HL7 v2 | Sample connector |
| FHIR STU3 | Sample connector |
| FHIR DSTU2 | Sample connector |
| Bulk FHIR NDJSON | Sample connector |
| OMOP CDM | Simplified connector |
| CPCDS | Simplified CSV connector |
| DICOM | Metadata-only connector |
| BFD RIF | Simplified CSV connector |

Some connectors have only been validated using small synthetic samples. Their implementation does not imply complete official specification compliance.

## Architecture

- **Backend:** Python, FastAPI
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript
- **Data Standards:** FHIR, C-CDA, HL7 v2, OMOP-style data
- **Security:** Password hashing and session-based authentication

## Project Structure

```text
MedBridge/
├── backend/
│   ├── api/
│   ├── canonical/
│   ├── core/
│   ├── fhir/
│   ├── identity/
│   ├── ccda/
│   ├── hl7v2/
│   ├── fhir_stu3/
│   ├── fhir_dstu2/
│   ├── fhir_ndjson/
│   ├── omop/
│   ├── cpcds/
│   ├── dicom/
│   ├── bfd_rif/
│   └── mock_hospital/
├── config/
├── data/
├── docs/
├── frontend/
├── mappings/
├── .gitignore
└── README.md
```

## Getting Started

### Requirements

- Python 3.10 or later
- pip

### Installation

Clone the repository:

```bash
git clone YOUR_REPOSITORY_URL
cd MedBridge
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

### Configure Environment Variables

Set the following variables before starting the API.

PowerShell example:

```powershell
$env:MEDBRIDGE_ENV = "development"
$env:MEDBRIDGE_SECRET = "REPLACE_WITH_A_RANDOM_SECRET"
$env:MEDBRIDGE_ADMIN_ID = "YOUR_TEST_ID"
$env:MEDBRIDGE_ADMIN_PASSWORD = "YOUR_TEST_PASSWORD"
```

Use your own values. Never commit actual passwords, session secrets, or local database files.

### Start the Mock Hospital

Open a terminal:

```powershell
cd backend
python -m uvicorn mock_hospital.main:app --reload --port 8001
```

### Start the MedBridge API

Open another terminal:

```powershell
cd backend
python -m uvicorn api.main:app --reload --port 8000
```

### Open the Application

- Web interface: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Mock Hospital API: http://127.0.0.1:8001

## Benchmark Results

The project includes technical tests using synthetic datasets.

### FHIR Conversion Performance

| Patients | Source Records | Conversion Time | Throughput |
|---:|---:|---:|---:|
| 1,000 | 3,000 | 0.482 sec | 2,073.65 patients/sec |
| 5,000 | 15,000 | 2.190 sec | 2,283.10 patients/sec |
| 10,000 | 30,000 | 4.674 sec | 2,139.30 patients/sec |

These historical measurements cover FHIR connector conversion, not the complete end-to-end pipeline. They have not yet been revalidated after the latest bug fixes.

### Identity Matching Test

A synthetic test fixture containing 6 patients and 15 candidate pairs produced:

- Precision: 100%
- Recall: 100%
- F1 Score: 100%

The identity matching audit counts MATCH and POSSIBLE_MATCH as positive detections. These results apply only to the six-patient synthetic fixture and its 15 candidate pairs. They do not represent confirmed identity matching accuracy or real-world clinical performance.

### Additional Tests

The benchmark reports also document:

- C-CDA parsing and field validation.
- Clinical data mapping checks.
- FHIR STU3 and DSTU2 sample conversion.
- OMOP-style and CPCDS-style data conversion.
- DICOM metadata extraction.
- BFD RIF-style data conversion.
- Sequential and concurrent API pipeline tests.

See `backend/MEDBRIDGE_MASTER_BENCHMARK_REPORT.md` for detailed results and limitations.

## Limitations

- Most standalone connectors have been tested with small synthetic samples.
- Some format implementations are simplified examples rather than complete standards implementations.
- DICOM testing covers metadata only, not image pixel data.
- Identity matching requires larger and more diverse datasets for meaningful evaluation.
- Production-scale database performance, full security validation, and large-scale load testing remain future work.
- The reported benchmarks are local development measurements and are not production performance guarantees.

## Security and Privacy

- Only synthetic data should be included in public test datasets.
- Passwords are hashed using PBKDF2-HMAC-SHA256.
- Session secrets and administrator credentials must be configured through environment variables.
- Local databases, uploaded files, and secrets should not be committed to the repository.

## Disclaimer

MedBridge is a technical development and research project. It is not a certified medical device, does not replace clinical judgment, and is not intended for diagnosis or treatment.

## License

No license has been selected yet. All rights reserved unless a license is added to this repository.
