import json
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

from config import WORKSPACES_DIR, GIT_CLONE_TIMEOUT, GIT_MAX_DEPTH

def is_valid_github_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "github.com"
        and len(parsed.path.strip("/").split("/")) == 2
    )

def generate_job_id() -> str:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(p for p in WORKSPACES_DIR.glob("job-*") if p.is_dir())
    return f"job-{len(existing) + 1:03d}"

def clone_github_repo(github_url: str):
    if not is_valid_github_url(github_url):
        raise ValueError("Only public GitHub repositories are allowed")

    job_id = generate_job_id()
    job_dir = WORKSPACES_DIR / job_id
    source_dir = job_dir / "source"

    try:
        source_dir.mkdir(parents=True, exist_ok=False)

        # Safe clone:
        # - shallow clone
        # - no submodules
        # - no tags
        cmd = [
            "git",
            "clone",
            "--depth", str(GIT_MAX_DEPTH),
            "--no-tags",
            "--single-branch",
            github_url,
            str(source_dir)
        ]

        subprocess.run(
            cmd,
            timeout=GIT_CLONE_TIMEOUT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        git_dir = source_dir / ".git"
        if git_dir.exists():
            subprocess.run(["rm", "-rf", str(git_dir)])
        
        metadata = {
            "job_id": job_id,
            "status": "ACCEPTED",
            "current_stage": "input_handling",
            "input": {
                "type": "github",
                "repository": github_url
            },
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        (job_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        return metadata
    
    except Exception:
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
        raise
