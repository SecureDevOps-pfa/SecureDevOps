from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from typing import Literal
from pydantic import BaseModel
import json
from config import WORKSPACES_DIR
from services.job_orchestrator import JobOrchestrator
from fastapi.responses import FileResponse
import zipfile
import tempfile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Secure DevSecOps Pipeline",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",  # Angular dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = JobOrchestrator()

# ---------- Models ----------

class Stack(BaseModel):
    language: str
    framework: str
    build_tool: str
    requires_db: bool = False


class Versions(BaseModel):
    java: str | None = None
    build_tool: str | None = None


class Pipeline(BaseModel):
    run_secret_scan: bool = False
    secret_scan_mode: Literal["dir", "git"] = "dir"
    run_build: bool = False
    run_unit_tests: bool = False
    run_sast: bool = False
    run_sca: bool = False
    run_package: bool = False
    run_smoke: bool = False
    run_dast: bool = False

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


@app.get("/api/jobs/{job_id}/status")
def get_job_status(job_id: str):
    job_dir = WORKSPACES_DIR / job_id

    # --------------------------------------------------
    # 1. Validate job exists
    # --------------------------------------------------
    if not job_dir.exists() or not job_dir.is_dir():
        raise HTTPException(status_code=404, detail="Job not found")

    metadata_path = job_dir / "metadata.json"
    if not metadata_path.exists():
        raise HTTPException(
            status_code=500,
            detail="Job metadata missing or corrupted"
        )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    state_path = job_dir / "state.json"

    # --------------------------------------------------
    # 2. Build static job block
    # --------------------------------------------------
    job_block = {
        "id": metadata.get("job_id"),
        "admission_status": metadata.get("status"),
        "created_at": metadata.get("created_at"),
        "stack": metadata.get("stack"),
        "versions": metadata.get("versions"),
    }

    # --------------------------------------------------
    # 3. Job still QUEUED (state.json not yet created)
    # --------------------------------------------------
    if not state_path.exists():
        stages = {}
        pipeline = metadata.get("pipeline", {})

        stage_map = [
            ("run_secret_scan", "SECRETS"),
            ("run_build", "BUILD"),
            ("run_unit_tests", "TEST"),
            ("run_sast", "SAST"),
            ("run_sca", "SCA"),
            ("run_package", "PACKAGE"),
            ("run_smoke", "SMOKE-TEST"),
            ("run_dast", "DAST"),
        ]

        for flag, stage in stage_map:
            stages[stage] = {
                "status": "PENDING" if pipeline.get(flag, False) else "SKIPPED",
                "message": None
            }

        return {
            "job": job_block,
            "execution": {
                "state": "QUEUED",
                "current_stage": None,
                "updated_at": metadata.get("created_at"),
                "stages": stages,
            },
        }

    # --------------------------------------------------
    # 4. Job RUNNING / FINISHED
    # --------------------------------------------------
    state = json.loads(state_path.read_text(encoding="utf-8"))

    execution_block = {
        "state": state.get("state"),
        "current_stage": state.get("current_stage"),
        "updated_at": state.get("updated_at"),
        "stages": state.get("stages", {}),
    }

    return {
        "job": job_block,
        "execution": execution_block,
    }


@app.get("/api/jobs/{job_id}/reports")
def download_job_reports(job_id: str):
    job_dir = WORKSPACES_DIR / job_id

    # --------------------------------------------------
    # 1. Validate job exists
    # --------------------------------------------------
    if not job_dir.exists() or not job_dir.is_dir():
        raise HTTPException(status_code=404, detail="Job not found")

    metadata_path = job_dir / "metadata.json"
    state_path = job_dir / "state.json"
    reports_dir = job_dir / "reports"

    if not metadata_path.exists():
        raise HTTPException(status_code=500, detail="Job metadata missing")

    if not state_path.exists():
        raise HTTPException(
            status_code=409,
            detail="Job has not started yet"
        )

    state = json.loads(state_path.read_text(encoding="utf-8"))

    # --------------------------------------------------
    # 2. Ensure job is finished
    # --------------------------------------------------
    if state.get("state") not in {"SUCCEEDED", "FAILED"}:
        raise HTTPException(
            status_code=409,
            detail="Job is still running"
        )

    if not reports_dir.exists() or not reports_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail="No reports available for this job"
        )

    # --------------------------------------------------
    # 3. Create ZIP archive (temp)
    # --------------------------------------------------
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        zip_path = tmp.name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in reports_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(reports_dir)
                zipf.write(file_path, arcname)

    # --------------------------------------------------
    # 4. Return ZIP file
    # --------------------------------------------------
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{job_id}-reports.zip",
    )

STAGE_LOG_FILES = {
    "SECRETS": ["secrets-dir.json", "secrets-git.json"],
    "BUILD": ["build.log"],
    "TEST": ["test.log"],
    "SAST": ["sast.json"],
    "SCA": ["sca.json"],
    "PACKAGE": ["package.log"],
    "SMOKE-TEST": ["smoke-test.log"],
    "DAST": ["dast.json"],
}

@app.get("/api/jobs/{job_id}/{stage}/logs")
def get_stage_logs(job_id: str, stage: str):
    stage = stage.upper()
    job_dir = WORKSPACES_DIR / job_id

    # --------------------------------------------------
    # 1. Validate job & state
    # --------------------------------------------------
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    state_path = job_dir / "state.json"
    if not state_path.exists():
        raise HTTPException(
            status_code=409,
            detail="Job has not started yet"
        )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    stages = state.get("stages", {})

    # --------------------------------------------------
    # 2. Validate stage
    # --------------------------------------------------
    if stage not in stages:
        raise HTTPException(status_code=404, detail="Stage not found")

    stage_status = stages[stage].get("status")

    if stage_status == "SKIPPED":
        raise HTTPException(
            status_code=404,
            detail=f"Stage {stage} was skipped"
        )

    if stage_status in {"PENDING", "RUNNING"}:
        raise HTTPException(
            status_code=409,
            detail=f"Stage {stage} is not finished yet"
        )

    # --------------------------------------------------
    # 3. Resolve log file
    # --------------------------------------------------
    stage_dir = job_dir / "reports" / stage.lower()

    if not stage_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No reports found for stage {stage}"
        )

    expected_files = STAGE_LOG_FILES.get(stage)
    if not expected_files:
        raise HTTPException(
            status_code=404,
            detail=f"No logs defined for stage {stage}"
        )

    for filename in expected_files:
        file_path = stage_dir / filename
        if file_path.exists():
            return FileResponse(
                file_path,
                media_type="application/octet-stream",
                filename=filename,
            )

    raise HTTPException(
        status_code=404,
        detail=f"No log file found for stage {stage}"
    )

# Swagger UI
# http://127.0.0.1:8000/docs

