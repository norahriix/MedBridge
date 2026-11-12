
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from core.pipeline import run_pipeline

app = FastAPI(
    title="MedBridge API",
    description="Software Interoperability Engine",
    version="1.0.0",
)


@app.get("/")
def home():
    return {
        "message": "Welcome to MedBridge",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/pipeline/run")
def run_pipeline_endpoint():
    result = run_pipeline()

    if result.status == "failed":
        raise HTTPException(status_code=500, detail="Pipeline failed")

    return result


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    project_root = Path(__file__).resolve().parents[2]
    return FileResponse(project_root / "frontend" / "index.html")
