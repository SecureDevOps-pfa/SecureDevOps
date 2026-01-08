import shutil
from pathlib import Path
from services.workspace_service import Workspace

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINES_ROOT = REPO_ROOT / "pipelines"


def install_pipelines(workspace: Workspace, framework: str):
    pipelines_dst = workspace.job_dir / "pipelines"

    # ---- install global pipelines (framework-independent) ----
    global_src = PIPELINES_ROOT / "global"
    global_dst = pipelines_dst / "global"

    if not global_src.exists():
        raise RuntimeError("Global pipelines directory not found")

    if global_dst.exists():
        shutil.rmtree(global_dst, ignore_errors=True)

    global_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(global_src, global_dst)

    # ---- install framework-specific pipelines ----
    framework_src = PIPELINES_ROOT / framework
    framework_dst = pipelines_dst / framework

    if not framework_src.exists():
        raise RuntimeError(f"Pipelines not found for framework: {framework}")

    if framework_dst.exists():
        shutil.rmtree(framework_dst, ignore_errors=True)

    shutil.copytree(framework_src, framework_dst)
