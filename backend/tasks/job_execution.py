import json
import subprocess
import platform

from pathlib import Path
from celery_app import celery_app
from config import WORKSPACES_DIR


@celery_app.task(bind=True, name="execute_job")
def execute_job(self, job_id: str):

    job_dir = WORKSPACES_DIR / job_id
    metadata = json.loads((job_dir / "metadata.json").read_text())

    _update_execution_state(job_dir, "RUNNING")

    try:
        _prepare_workspace_permissions(job_dir)
        _init_reports_volume(metadata["job_id"])
        _run_runner_container(job_dir, metadata)
        _update_execution_state(job_dir, "SUCCEEDED")

    except Exception as exc:
        _update_execution_state(job_dir, "FAILED", str(exc))
        raise

    finally:
        # Cleanup Docker volume (OS-independent)
        subprocess.run(
            ["docker", "volume", "rm", f"reports-{job_id}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


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

def _docker_user_args():
    return ["-u", "10001:10001"]

def _init_reports_volume(job_id: str):
    """
    Ensure the reports volume is writable by UID 10001
    """
    volume_name = f"reports-{job_id}"

    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{volume_name}:/home/runner/reports",
            "busybox",
            "sh", "-c", "chown -R 10001:10001 /home/runner/reports"
        ],
        check=True
    )


def _run_runner_container(job_dir: Path, metadata: dict):
    """
    Run the Docker runner and execute pipeline scripts.
    """

    image = _select_runner_image(metadata)
    job_id = job_dir.name

    subprocess.run(
        [
            "docker", "run", "--rm",

            *_docker_user_args(),

            # MUST be f-strings
            "-e", f"APP_DIR=/home/runner/workspaces/{job_id}/source",
            "-e", f"PIPELINES_DIR=/home/runner/workspaces/{job_id}/pipelines",
            "-e", "REPORTS_DIR=/home/runner/reports",

            # mount named volume
            "-v", "securedevops_workspaces:/home/runner/workspaces",

            # reports volume stays as-is
            "-v", f"reports-{job_id}:/home/runner/reports",

            "-w", "/home/runner",
            image,
            "bash", "-c", _pipeline_command(metadata),
        ],
        check=True,
    )

def _pipeline_command(metadata: dict) -> str:
    """
    Build pipeline execution command based on metadata.
    (Minimal version for deadline.)
    """

    pipeline = metadata.get("pipeline", {})
    pipeline_dir = _resolve_pipeline_dir(metadata)

    base = f"$PIPELINES_DIR/{pipeline_dir}"

    commands = []

    def stage(name: str, cmd: str):
        return (
            f'echo "[PIPELINE] START {name}" && '
            f'{cmd} && '
            f'echo "[PIPELINE] END {name}"'
        )

    if pipeline.get("run_build", True):
        commands.append(stage("BUILD", f"bash {base}/build.sh"))

    if pipeline.get("run_unit_tests", True):
        commands.append(stage("TEST", f"bash {base}/test.sh"))

    if pipeline.get("run_sast", False):
        commands.append(stage("SAST", f"bash {base}/sast.sh"))

    if pipeline.get("run_sca", False):
        commands.append(stage("SCA", f"bash {base}/sca.sh"))

    if pipeline.get("run_secret_scan", False):
        commands.append(stage("SECRETS", f"bash {base}/secrets.sh"))

    return " && ".join(commands)


def _select_runner_image(metadata: dict) -> str:
    """
    Select Docker runner image based on stack metadata.
    Minimal mapping for now.
    """

    stack = metadata.get("stack", {})

    if stack.get("language") == "java" and stack.get("build_tool") == "maven":
        return "abderrahmane03/pipelinex:java17-mvn3.9.12-latest"

    raise RuntimeError("Unsupported stack for runner selection")


def _update_execution_state(
    job_dir: Path,
    state: str,
    error: str | None = None,
):
    """
    Persist execution state for the job.
    """

    state_file = job_dir / "state.json"

    payload = {
        "state": state,
    }

    if error:
        payload["error"] = error

    state_file.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

def _resolve_pipeline_dir(metadata: dict) -> str:
    stack = metadata.get("stack", {})

    framework = stack.get("framework")
    build_tool = stack.get("build_tool")

    if not framework or not build_tool:
        raise RuntimeError("Invalid metadata: missing framework or build_tool")

    return f"{framework}-{build_tool}"
