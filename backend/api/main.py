import secrets
import os
import json
import csv
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from core.pipeline import run_pipeline
from api.auth import init_db, verify_user


app = FastAPI(
    title="MedBridge API",
    description="Clinical Data Interoperability Platform",
    version="1.2.0"
)

secret_key = os.getenv("MEDBRIDGE_SECRET")

if not secret_key:
    if os.getenv("MEDBRIDGE_ENV", "development").lower() == "production":
        raise RuntimeError("MEDBRIDGE_SECRET must be set in production")
    secret_key = secrets.token_urlsafe(32)

app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key,
    same_site="lax",
    https_only=False,
    max_age=3600
)

init_db()

API_FOLDER = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = API_FOLDER / "medbridge.db"

UPLOAD_FOLDER = PROJECT_ROOT / "uploads" / "hospitals"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".json", ".csv"}
MAX_FILE_SIZE = 15 * 1024 * 1024

CANONICAL_FIELDS = [
    "source_patient_id",
    "national_id",
    "name",
    "birth_date",
    "gender"
]

FIELD_ALIASES = {
    "source_patient_id": [
        "patient_id", "patientid", "id", "medical_record_number",
        "mrn", "file_number", "رقم_الملف"
    ],
    "national_id": [
        "national_id", "nationalid", "identity", "identity_number",
        "iqama", "رقم_الهوية"
    ],
    "name": [
        "name", "patient_name", "fullname", "full_name",
        "patientname", "الاسم", "اسم_المريض"
    ],
    "birth_date": [
        "birth_date", "dob", "date_of_birth", "birthdate",
        "dateofbirth", "تاريخ_الميلاد"
    ],
    "gender": ["gender", "sex", "patient_gender", "الجنس"]
}


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_medbridge_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_results (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS conflict_decisions (
                conflict_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                selected_value TEXT,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS hospitals (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE,
                city TEXT NOT NULL,
                system_name TEXT NOT NULL,
                data_format TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                mapping_json TEXT NOT NULL DEFAULT '{}',
                test_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS hospital_files (
                id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY(hospital_id)
                    REFERENCES hospitals(id)
                    ON DELETE CASCADE
            )
        """)


init_medbridge_db()


class LoginData(BaseModel):
    identity: str
    password: str


class ConflictDecisionData(BaseModel):
    action: Literal["confirm", "reject"]
    selected_value: str | None = None
    reason: str


class HospitalCreateData(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    city: str = Field(min_length=2, max_length=100)
    system_name: str = Field(min_length=2, max_length=100)
    data_format: Literal["JSON", "CSV"]
    code: str | None = None


class HospitalUpdateData(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    system_name: str | None = Field(default=None, min_length=2, max_length=100)
    data_format: Literal["JSON", "CSV"] | None = None


class HospitalMappingData(BaseModel):
    mapping: dict[str, str]


def require_login(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول أولاً")
    return user_id


def save_pipeline_result(result):
    result_data = result.model_dump(mode="json")
    result_json = json.dumps(result_data, ensure_ascii=False)

    with get_db() as db:
        db.execute("""
            INSERT INTO pipeline_results (id, result_json, created_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                result_json = excluded.result_json,
                created_at = excluded.created_at
        """, (result_json, datetime.now().isoformat()))

    return result_data


def get_saved_pipeline():
    with get_db() as db:
        row = db.execute("""
            SELECT result_json, created_at
            FROM pipeline_results WHERE id = 1
        """).fetchone()

    if row is None:
        return None

    result = json.loads(row["result_json"])
    result["created_at"] = row["created_at"]
    return result


def get_conflict_decisions():
    with get_db() as db:
        rows = db.execute("""
            SELECT conflict_id, patient_id, user_id, action,
                   selected_value, reason, created_at
            FROM conflict_decisions
            ORDER BY created_at DESC
        """).fetchall()

    return [dict(row) for row in rows]


def get_hospital_or_404(hospital_id):
    with get_db() as db:
        hospital = db.execute(
            "SELECT * FROM hospitals WHERE id = ?",
            (hospital_id,)
        ).fetchone()

    if hospital is None:
        raise HTTPException(status_code=404, detail="المستشفى غير موجود")

    return dict(hospital)


def hospital_response(hospital):
    result = dict(hospital)

    result["mapping"] = json.loads(result.pop("mapping_json", "{}"))

    test_json = result.pop("test_json", None)
    result["test_result"] = json.loads(test_json) if test_json else None

    return result


def get_hospital_files(hospital_id):
    with get_db() as db:
        rows = db.execute("""
            SELECT id, original_name, file_type, file_size, uploaded_at
            FROM hospital_files
            WHERE hospital_id = ?
            ORDER BY uploaded_at DESC
        """, (hospital_id,)).fetchall()

    return [dict(row) for row in rows]


def read_uploaded_records(file_path):
    extension = file_path.suffix.lower()

    if extension == ".json":
        with file_path.open("r", encoding="utf-8-sig") as file:
            records = json.load(file)

    elif extension == ".csv":
        with file_path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            records = list(csv.DictReader(file))

    else:
        raise ValueError("صيغة الملف غير مدعومة")

    if not isinstance(records, list):
        raise ValueError("يجب أن يحتوي الملف على قائمة من السجلات")

    if not all(isinstance(item, dict) for item in records):
        raise ValueError("يجب أن يكون كل سجل عبارة عن مجموعة حقول")

    return records


def suggest_mapping(columns):
    suggestions = {}
    normalized_columns = {
        str(column).strip().lower(): str(column)
        for column in columns
    }

    for canonical_field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias.lower() in normalized_columns:
                suggestions[canonical_field] = normalized_columns[alias.lower()]
                break

    return suggestions


@app.get("/")
@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(PROJECT_ROOT / "frontend" / "index.html")


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/login")
def login(data: LoginData, request: Request):
    if not verify_user(data.identity, data.password):
        raise HTTPException(
            status_code=401,
            detail="رقم الهوية أو الرمز السري غير صحيح"
        )

    request.session.clear()
    request.session["user_id"] = data.identity
    return {"status": "success"}


@app.get("/me")
def current_user(request: Request):
    return {"identity": require_login(request)}


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"status": "logged out"}


@app.post("/pipeline/run")
def run_pipeline_endpoint(request: Request):
    require_login(request)

    try:
        result = run_pipeline()

        if result.status == "failed":
            raise HTTPException(
                status_code=500,
                detail="فشلت المعالجة: " + "; ".join(result.errors)
            )

        result_data = save_pipeline_result(result)
        result_data["review_decisions"] = get_conflict_decisions()
        return result_data

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"حدث خطأ أثناء المعالجة: {str(error)}"
        )


@app.get("/pipeline/latest")
def latest_pipeline_endpoint(request: Request):
    require_login(request)

    result = get_saved_pipeline()
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="لا توجد نتائج معالجة محفوظة"
        )

    result["review_decisions"] = get_conflict_decisions()
    return result


@app.get("/conflicts")
def list_conflicts(request: Request):
    require_login(request)

    result = get_saved_pipeline()
    if result is None:
        return []

    decisions = {
        item["conflict_id"]: item
        for item in get_conflict_decisions()
    }

    patients_result = result.get("patients", [])
    patient_names = {}

    for patient in patients_result:
        patient_id = (
            patient.get("id")
            or patient.get("patient_id")
        )
        if patient_id:
            patient_names[str(patient_id)] = (
                patient.get("name")
                or patient.get("full_name")
                or patient.get("patient_name")
                or ""
            )

    conflicts = result.get("conflicts", [])

    output = []
    for conflict in conflicts:
        item = dict(conflict)

        patient_id = str(item.get("patient_id") or "")
        item["patient_name"] = (
            item.get("patient_name")
            or patient_names.get(patient_id)
            or ""
        )

        item["decision"] = decisions.get(item.get("id"))
        output.append(item)

    return output



@app.post("/conflicts/{conflict_id}/decision")
def save_conflict_decision(
    conflict_id: str,
    data: ConflictDecisionData,
    request: Request
):
    user_id = require_login(request)

    if not data.reason.strip():
        raise HTTPException(status_code=400, detail="يجب كتابة سبب القرار")

    result = get_saved_pipeline()
    if result is None:
        raise HTTPException(status_code=404, detail="لا توجد نتائج معالجة")

    conflict = next(
        (
            item for item in result.get("conflicts", [])
            if item.get("id") == conflict_id
        ),
        None
    )

    if conflict is None:
        raise HTTPException(status_code=404, detail="التعارض غير موجود")

    selected_value = data.selected_value

    if data.action == "confirm":
        if selected_value is None:
            raise HTTPException(
                status_code=400,
                detail="يجب اختيار القيمة المراد اعتمادها"
            )

        available_values = [
            str(value) for value in conflict.get("values", [])
        ]

        if selected_value not in available_values:
            raise HTTPException(
                status_code=400,
                detail="القيمة المختارة ليست من القيم المسجلة"
            )
    else:
        selected_value = None

    created_at = datetime.now().isoformat()

    with get_db() as db:
        db.execute("""
            INSERT INTO conflict_decisions (
                conflict_id, patient_id, user_id, action,
                selected_value, reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(conflict_id) DO UPDATE SET
                patient_id = excluded.patient_id,
                user_id = excluded.user_id,
                action = excluded.action,
                selected_value = excluded.selected_value,
                reason = excluded.reason,
                created_at = excluded.created_at
        """, (
            conflict_id,
            conflict.get("patient_id", ""),
            user_id,
            data.action,
            selected_value,
            data.reason.strip(),
            created_at
        ))

    return {
        "status": "saved",
        "conflict_id": conflict_id,
        "action": data.action,
        "selected_value": selected_value,
        "reason": data.reason.strip(),
        "created_at": created_at
    }


@app.post("/hospitals")
def create_hospital(data: HospitalCreateData, request: Request):
    require_login(request)

    hospital_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    code = (data.code or f"MB-{uuid.uuid4().hex[:8]}").strip().upper()

    with get_db() as db:
        try:
            db.execute("""
                INSERT INTO hospitals (
                    id, name, code, city, system_name, data_format,
                    status, mapping_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'draft', '{}', ?, ?)
            """, (
                hospital_id,
                data.name.strip(),
                code,
                data.city.strip(),
                data.system_name.strip(),
                data.data_format,
                now,
                now
            ))
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail="رمز المستشفى مستخدم مسبقًا"
            )

    (UPLOAD_FOLDER / hospital_id).mkdir(parents=True, exist_ok=True)

    hospital = get_hospital_or_404(hospital_id)
    result = hospital_response(hospital)
    result["files"] = []
    return result


@app.get("/hospitals")
def list_hospitals(request: Request):
    require_login(request)

    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM hospitals ORDER BY created_at DESC
        """).fetchall()

    result = []
    for row in rows:
        item = hospital_response(dict(row))
        item["files"] = get_hospital_files(item["id"])
        result.append(item)

    return result


@app.get("/hospitals/{hospital_id}")
def get_hospital_details(hospital_id: str, request: Request):
    require_login(request)

    hospital = hospital_response(get_hospital_or_404(hospital_id))
    hospital["files"] = get_hospital_files(hospital_id)
    return hospital


@app.put("/hospitals/{hospital_id}")
def update_hospital(
    hospital_id: str,
    data: HospitalUpdateData,
    request: Request
):
    require_login(request)
    get_hospital_or_404(hospital_id)

    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="لا توجد بيانات للتعديل")

    allowed = {"name", "city", "system_name", "data_format"}
    updates = {key: value for key, value in updates.items() if key in allowed}

    for key, value in updates.items():
        if isinstance(value, str):
            updates[key] = value.strip()

    updates["updated_at"] = datetime.now().isoformat()

    assignments = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [hospital_id]

    with get_db() as db:
        db.execute(
            f"UPDATE hospitals SET {assignments} WHERE id = ?",
            values
        )

    hospital = hospital_response(get_hospital_or_404(hospital_id))
    hospital["files"] = get_hospital_files(hospital_id)
    return hospital


@app.post("/hospitals/{hospital_id}/upload")
async def upload_hospital_file(
    hospital_id: str,
    request: Request,
    file: UploadFile = File(...)
):
    require_login(request)
    get_hospital_or_404(hospital_id)

    original_name = Path(file.filename or "uploaded_file").name
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="الصيغ المتاحة حاليًا JSON وCSV فقط"
        )

    content = await file.read(MAX_FILE_SIZE + 1)
    await file.close()

    if not content:
        raise HTTPException(status_code=400, detail="الملف فارغ")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="حجم الملف أكبر من الحد المسموح (15 MB)"
        )

    hospital_folder = UPLOAD_FOLDER / hospital_id
    hospital_folder.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}{extension}"
    file_path = hospital_folder / stored_name

    try:
        file_path.write_bytes(content)
        records = read_uploaded_records(file_path)
        if not records:
            raise ValueError("الملف لا يحتوي على سجلات")
    except Exception as error:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=400,
            detail=f"تعذر قراءة الملف: {str(error)}"
        )

    file_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    with get_db() as db:
        db.execute("""
            INSERT INTO hospital_files (
                id, hospital_id, original_name, stored_name,
                file_type, file_size, uploaded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id, hospital_id, original_name, stored_name,
            extension.replace(".", "").upper(), len(content), now
        ))

        db.execute("""
            UPDATE hospitals
            SET status = 'draft', test_json = NULL, updated_at = ?
            WHERE id = ?
        """, (now, hospital_id))

    return {
        "status": "uploaded",
        "file_id": file_id,
        "file_name": original_name,
        "records_count": len(records),
        "format": extension.replace(".", "").upper()
    }


@app.post("/hospitals/{hospital_id}/analyze")
def analyze_hospital_files(hospital_id: str, request: Request):
    require_login(request)
    get_hospital_or_404(hospital_id)

    with get_db() as db:
        files = db.execute("""
            SELECT * FROM hospital_files
            WHERE hospital_id = ?
            ORDER BY uploaded_at DESC
        """, (hospital_id,)).fetchall()

    if not files:
        raise HTTPException(
            status_code=400,
            detail="ارفعي ملفًا واحدًا على الأقل أولًا"
        )

    analyzed_files = []

    for item in files:
        file_path = UPLOAD_FOLDER / hospital_id / item["stored_name"]

        try:
            records = read_uploaded_records(file_path)
            columns = list(records[0].keys()) if records else []

            analyzed_files.append({
                "file_id": item["id"],
                "file_name": item["original_name"],
                "records_count": len(records),
                "columns": columns,
                "suggested_mapping": suggest_mapping(columns)
            })
        except Exception as error:
            analyzed_files.append({
                "file_id": item["id"],
                "file_name": item["original_name"],
                "error": str(error)
            })

    return {
        "hospital_id": hospital_id,
        "files": analyzed_files,
        "canonical_fields": CANONICAL_FIELDS
    }


@app.put("/hospitals/{hospital_id}/mapping")
def save_hospital_mapping(
    hospital_id: str,
    data: HospitalMappingData,
    request: Request
):
    require_login(request)
    get_hospital_or_404(hospital_id)

    mapping = data.mapping

    invalid_fields = [
        field for field in mapping if field not in CANONICAL_FIELDS
    ]
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"حقول موحدة غير معروفة: {invalid_fields}"
        )

    if len(set(mapping.values())) != len(mapping.values()):
        raise HTTPException(
            status_code=400,
            detail="لا يمكن ربط العمود نفسه بأكثر من حقل موحد"
        )

    now = datetime.now().isoformat()

    with get_db() as db:
        db.execute("""
            UPDATE hospitals
            SET mapping_json = ?, status = 'draft',
                test_json = NULL, updated_at = ?
            WHERE id = ?
        """, (
            json.dumps(mapping, ensure_ascii=False),
            now,
            hospital_id
        ))

    return {"status": "saved", "mapping": mapping}


@app.post("/hospitals/{hospital_id}/test")
def test_hospital(hospital_id: str, request: Request):
    require_login(request)

    hospital = get_hospital_or_404(hospital_id)
    mapping = json.loads(hospital["mapping_json"])

    errors = []
    warnings = []

    required_fields = [
        "source_patient_id", "name", "birth_date", "gender"
    ]

    for field in required_fields:
        if not mapping.get(field):
            errors.append(f"لم يتم ربط الحقل المطلوب: {field}")

    with get_db() as db:
        files = db.execute("""
            SELECT * FROM hospital_files
            WHERE hospital_id = ?
            ORDER BY uploaded_at DESC
        """, (hospital_id,)).fetchall()

    if not files:
        errors.append("لم يتم رفع أي ملفات")

    tested_records = 0
    valid_records = 0

    if not errors:
        for item in files:
            file_path = UPLOAD_FOLDER / hospital_id / item["stored_name"]

            try:
                records = read_uploaded_records(file_path)

                for index, record in enumerate(records, start=1):
                    tested_records += 1
                    record_errors = []

                    for canonical_field in required_fields:
                        source_field = mapping.get(canonical_field)
                        value = record.get(source_field)

                        if value is None or str(value).strip() == "":
                            record_errors.append(
                                f"السجل {index}: الحقل {canonical_field} فارغ"
                            )

                    if record_errors:
                        errors.extend(record_errors[:20])
                    else:
                        valid_records += 1

            except Exception as error:
                errors.append(
                    f"تعذر اختبار {item['original_name']}: {str(error)}"
                )

    passed = (
        not errors
        and tested_records > 0
        and valid_records == tested_records
    )

    if tested_records > valid_records:
        warnings.append("توجد سجلات تحتاج إلى تصحيح قبل اعتماد المستشفى")

    test_result = {
        "passed": passed,
        "tested_records": tested_records,
        "valid_records": valid_records,
        "errors": errors[:50],
        "warnings": warnings,
        "tested_at": datetime.now().isoformat()
    }

    with get_db() as db:
        db.execute("""
            UPDATE hospitals
            SET test_json = ?, status = ?, updated_at = ?
            WHERE id = ?
        """, (
            json.dumps(test_result, ensure_ascii=False),
            "tested" if passed else "draft",
            datetime.now().isoformat(),
            hospital_id
        ))

    return test_result


@app.post("/hospitals/{hospital_id}/activate")
def activate_hospital(hospital_id: str, request: Request):
    require_login(request)

    hospital = get_hospital_or_404(hospital_id)

    if not hospital["test_json"]:
        raise HTTPException(
            status_code=400,
            detail="يجب اختبار ملفات المستشفى أولًا"
        )

    test_result = json.loads(hospital["test_json"])

    if not test_result.get("passed"):
        raise HTTPException(
            status_code=400,
            detail="لم يجتز المستشفى الاختبار. راجعي الأخطاء أولًا"
        )

    now = datetime.now().isoformat()

    with get_db() as db:
        db.execute("""
            UPDATE hospitals
            SET status = 'configured', updated_at = ?
            WHERE id = ?
        """, (now, hospital_id))

    return {
        "status": "configured",
        "message": (
            "تم اعتماد إعدادات المستشفى واجتياز اختبار الملفات. "
            "هذا لا يعني وجود اتصال مباشر بنظام المستشفى."
        ),
        "hospital_id": hospital_id
    }
