
from fastapi import FastAPI

app = FastAPI(
    title="MedBridge API",
    description="Software Interoperability Engine",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Welcome to MedBridge",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
