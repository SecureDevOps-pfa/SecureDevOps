# backend/app.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from pydantic import BaseModel

from services.upload_service import handle_zip_upload
from services.github_service import clone_github_repo

app = FastAPI(
    title="Secure DevSecOps Pipeline",
    version="1.0.0"
)

class GitHubRequest(BaseModel):
    github_url: str


# ---------- Endpoints ----------

@app.post("/api/jobs/upload", status_code=201)
async def create_job_from_zip(
    project_zip: UploadFile = File(...)
):
    if not project_zip.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are allowed"
        )

    try:
        return handle_zip_upload(project_zip)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/jobs/github", status_code=201)
async def create_job_from_github(
    payload: GitHubRequest
):
    try:
        return clone_github_repo(payload.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



#http://127.0.0.1:8000/docs
