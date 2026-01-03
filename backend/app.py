from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
import json

from services.job_orchestrator import JobOrchestrator

app = FastAPI(
    title="Secure DevSecOps Pipeline",
    version="1.0.0"
)

orchestrator = JobOrchestrator()

# ---------- Models ----------

class Stack(BaseModel):
    language: str
    framework: str
    build_tool: str


class Versions(BaseModel):
    java: str | None = None
    build_tool: str | None = None


class Pipeline(BaseModel):
    run_build: bool = True
    run_unit_tests: bool = True
    run_sast: bool = True
    run_sca: bool = True
    run_secret_scan: bool = True


class GitHubJobRequest(BaseModel):
    github_url: str
    stack: Stack
    versions: Versions
    pipeline: Pipeline


# ---------- Endpoints ----------

@app.post("/api/jobs/upload", status_code=201)
async def create_job_from_zip(
    project_zip: UploadFile = File(...),
    metadata: str = Form(...)
):
    if not project_zip.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

    try:
        meta = json.loads(metadata)
        return orchestrator.create_job_from_zip_input(
            file=project_zip,
            metadata=meta
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/jobs/github", status_code=201)
async def create_job_from_github(payload: GitHubJobRequest):
    try:
        return orchestrator.create_job_from_repo_input(
            github_url=payload.github_url,
            metadata=payload.dict()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Swagger UI
# http://127.0.0.1:8000/docs

