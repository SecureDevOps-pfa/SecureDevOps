import shutil
from pathlib import Path
from dataclasses import dataclass

from config import WORKSPACES_DIR


@dataclass
class Workspace:
    job_id: str
    job_dir: Path
    source_dir: Path


def _generate_job_id() -> str:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(p for p in WORKSPACES_DIR.glob("job-*") if p.is_dir())
    return f"job-{len(existing) + 1:03d}"


def create_workspace() -> Workspace:
    job_id = _generate_job_id()
    job_dir = WORKSPACES_DIR / job_id
    source_dir = job_dir / "source"

    job_dir.mkdir()
    source_dir.mkdir()
    (job_dir / "pipelines").mkdir()

    return Workspace(
        job_id=job_id,
        job_dir=job_dir,
        source_dir=source_dir,
    )

def cleanup_workspace(workspace: Workspace):
    if workspace.job_dir.exists():
        shutil.rmtree(workspace.job_dir, ignore_errors=True)
