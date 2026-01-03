import shutil
from pathlib import Path
from services.workspace_service import Workspace

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINES_ROOT = REPO_ROOT / "pipelines"


def install_pipelines(workspace: Workspace, framework: str):
    src = PIPELINES_ROOT / framework
    dst = workspace.job_dir / "pipelines" / framework

    if not src.exists():
        raise RuntimeError(f"Pipelines not found for framework: {framework}")

    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)

