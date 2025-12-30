from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
import json
import shutil

from services.upload_service import handle_zip_upload
from services.github_service import clone_github_repo
from services.job_service import finalize_job

app = FastAPI(
    title="Secure DevSecOps Pipeline",
    version="1.0.0"
)

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
    """
    ZIP upload + structure declaration.
    """

    if not project_zip.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

    try:
        meta = json.loads(metadata)

        job_dir, source_dir = handle_zip_upload(project_zip)

        return finalize_job(
            job_dir=job_dir,
            source_dir=source_dir,
            stack=meta["stack"],
            versions=meta.get("versions", {}),
            pipeline=meta["pipeline"],
        )

    except (ValueError, KeyError) as e:
        if "job_dir" in locals() and job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/jobs/github", status_code=201)
async def create_job_from_github(
    payload: GitHubJobRequest
):
    """
    GitHub clone + structure declaration.
    """

    try:
        job_dir, source_dir = clone_github_repo(payload.github_url)

        return finalize_job(
            job_dir=job_dir,
            source_dir=source_dir,
            stack=payload.stack.dict(),
            versions=payload.versions.dict(),
            pipeline=payload.pipeline.dict(),
        )

    except ValueError as e:
        if "job_dir" in locals() and job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e))


# Swagger UI
# http://127.0.0.1:8000/docs
