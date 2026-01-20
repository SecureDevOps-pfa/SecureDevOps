from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from typing import Literal
from pydantic import BaseModel
import json
from config import WORKSPACES_DIR
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
                "status": "PENDING" if pipeline.get(flag, False) else "SKIPPED"
            }

        return {
            "job": job_block,
            "execution": {
                "state": "QUEUED",
                "current_stage": None,
                "updated_at": metadata.get("created_at"),
                "stages": stages,
                "warnings": {},
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
        "warnings": state.get("warnings", {}),
    }

    return {
        "job": job_block,
        "execution": execution_block,
    }


# Swagger UI
# http://127.0.0.1:8000/docs

