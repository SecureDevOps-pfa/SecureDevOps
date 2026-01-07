import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from celery_app import celery_app
from config import WORKSPACES_DIR


PIPELINE_STAGES = [
    ("run_secret_scan", "SECRETS"),
    ("run_build", "BUILD"),
    ("run_unit_tests", "TEST"),
    ("run_sast", "SAST"),
    ("run_sca", "SCA"),
    ("run_package", "PACKAGE"),
    ("run_smoke", "SMOKE-TEST"),
    ("run_dast", "DAST"),
]

BLOCKING_STAGES = {
    "BUILD",
    "PACKAGE",
    "SMOKE-TEST",
}


@celery_app.task(bind=True, name="execute_job")
def execute_job(self, job_id: str):
    job_dir = WORKSPACES_DIR / job_id
    metadata = json.loads((job_dir / "metadata.json").read_text())

    try:
        _prepare_workspace_permissions(job_dir)
        # ensure reports directory exists inside workspace
        (job_dir / "reports").mkdir(parents=True, exist_ok=True)

        stages = _resolve_pipeline_stages(metadata)
        _init_state(job_dir, stages)

        _start_runner_container(job_id, metadata)

        for stage, status in stages.items():
            if status == "PENDING":
                _run_stage(job_dir, job_id, metadata, stage)

        _finalize_job(job_dir, success=True)

    except Exception as exc:
        _finalize_job(job_dir, success=False, error=str(exc))
        raise

    finally:
        _stop_runner_container(job_id)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _prepare_workspace_permissions(job_dir: Path):
    subprocess.run(
        ["chown", "-R", "10001:10001", str(job_dir)],
        check=True,
    )

    subprocess.run(
        ["chmod", "-R", "u+rwx", str(job_dir)],
        check=True,
    )

    pipelines_dir = job_dir / "pipelines"
    if pipelines_dir.exists():
        for script in pipelines_dir.glob("*.sh"):
            script.chmod(0o755)


def _resolve_pipeline_stages(metadata: dict) -> dict:
    """
    Returns:
    {
      "SECRETS": "SKIPPED",
      "BUILD": "PENDING",
      "TEST": "PENDING",
      ...
    }
    """
    pipeline = metadata.get("pipeline", {})

    stages = {}
    for flag, stage in PIPELINE_STAGES:
        if pipeline.get(flag, False):
            stages[stage] = "PENDING"
        else:
            stages[stage] = "SKIPPED"

    return stages


def _init_state(job_dir: Path, stages: dict):
    state = {
        "state": "RUNNING",
        "current_stage": None,
        "updated_at": _now(),
        "stages": {
            stage: {"status": status}
            for stage, status in stages.items()
        },
    }
    _write_state(job_dir, state)


def _write_state(job_dir: Path, payload: dict):
    (job_dir / "state.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _start_runner_container(job_id: str, metadata: dict):
    image = _select_runner_image(metadata)

    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", f"runner-{job_id}",
            "-u", "10001:10001",

            "-e", f"APP_DIR=/home/runner/workspaces/{job_id}/source",
            "-e", f"PIPELINES_DIR=/home/runner/workspaces/{job_id}/pipelines",
            "-e", f"REPORTS_DIR=/home/runner/workspaces/{job_id}/reports",

            "-v", "securedevops_workspaces:/home/runner/workspaces",

            "-w", "/home/runner",
            image,
            "tail", "-f", "/dev/null",
        ],
        check=True,
    )


def _select_runner_image(metadata: dict) -> str:
    stack = metadata.get("stack", {})

    if stack.get("language") == "java" and stack.get("build_tool") == "maven":
        return "abderrahmane03/pipelinex:java17-mvn3.9.12-latest"

    raise RuntimeError("Unsupported stack for runner selection")


def _run_stage(
    job_dir: Path,
    job_id: str,
    metadata: dict,
    stage: str,
):
    state = _read_state(job_dir)

    # update state → RUNNING
    state["current_stage"] = stage
    state["stages"][stage]["status"] = "RUNNING"
    state["updated_at"] = _now()
    _write_state(job_dir, state)

    # CREATE STAGE-SPECIFIC REPORT DIRECTORY WITH PROPER PERMISSIONS
    stage_report_dir = job_dir / "reports" / stage.lower()
    stage_report_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure the stage report directory has proper permissions
    subprocess.run(
        ["chown", "-R", "10001:10001", str(stage_report_dir)],
        check=True,
    )
    subprocess.run(
        ["chmod", "-R", "u+rwx", str(stage_report_dir)],
        check=True,
    )

    pipeline_dir = _resolve_pipeline_dir(metadata)
    stage_script = f"$PIPELINES_DIR/{pipeline_dir}/{stage.lower()}.sh"

    subprocess.run(
        [
            "docker", "exec",
            f"runner-{job_id}",
            "bash", "-lc",
            f"bash {stage_script}",
        ],
        check=False,
    )

    try:
        raw = subprocess.check_output(
            [
                "docker", "exec", f"runner-{job_id}",
                "bash", "-lc",
                f"cat $REPORTS_DIR/{stage.lower()}/result.json",
            ],
            text=True,
        )
    except subprocess.CalledProcessError:
        raise RuntimeError(
            f"{stage} did not produce result.json in workspace reports directory"
        )

    result = json.loads(raw)

    if result["status"] == "SUCCESS":
        state["stages"][stage]["status"] = "SUCCESS"
        state["updated_at"] = _now()
        _write_state(job_dir, state)
        return

    # FAILURE (stage-level)
    state["stages"][stage]["status"] = "FAILED"
    state["updated_at"] = _now()

    if stage in BLOCKING_STAGES:
        state["state"] = "FAILED"
        state["error"] = result.get("message", "blocking stage failed")
        _write_state(job_dir, state)
        raise RuntimeError(f"Blocking stage {stage} failed")

    # non-blocking failure → continue pipeline
    state.setdefault("warnings", {})
    state["warnings"][stage] = result.get("message", "stage failed")
    _write_state(job_dir, state)


def _read_state(job_dir: Path) -> dict:
    return json.loads((job_dir / "state.json").read_text())


def _resolve_pipeline_dir(metadata: dict) -> str:
    stack = metadata.get("stack", {})

    framework = stack.get("framework")
    build_tool = stack.get("build_tool")

    if not framework or not build_tool:
        raise RuntimeError("Invalid metadata: missing framework or build_tool")

    return f"{framework}-{build_tool}"


def _finalize_job(
    job_dir: Path,
    success: bool,
    error: str | None = None,
):
    state = _read_state(job_dir)
    state["state"] = "SUCCEEDED" if success else "FAILED"
    state["current_stage"] = None
    state["updated_at"] = _now()

    if error:
        state["error"] = error

    _write_state(job_dir, state)


def _stop_runner_container(job_id: str):
    subprocess.run(
        ["docker", "rm", "-f", f"runner-{job_id}"],
        check=False,
    )
