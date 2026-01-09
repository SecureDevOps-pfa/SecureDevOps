import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from celery_app import celery_app
from config import WORKSPACES_DIR, HOST_WORKSPACES_PATH


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

SECRETS_SCRIPT_BY_MODE = {
    "dir": "secrets-dir.sh",
    "git": "secrets-git.sh",
}


@celery_app.task(bind=True, name="execute_job")
def execute_job(self, job_id: str):
    job_dir = WORKSPACES_DIR / job_id
    metadata = json.loads((job_dir / "metadata.json").read_text())

    try:
        # Ensure reports directory exists inside workspace
        (job_dir / "reports").mkdir(parents=True, exist_ok=True)

        # Set permissions so runner container (UID 10001) can access
        _prepare_workspace_permissions(job_dir)
        
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
    """
    Set permissions recursively so runner container (UID 10001) can access.
    Uses os.chmod() which works with bind mounts.
    """
    for root, dirs, files in os.walk(job_dir):
        # Set directory permissions to 777 (rwxrwxrwx)
        try:
            os.chmod(root, 0o777)
        except Exception as e:
            print(f"Warning: Could not chmod {root}: {e}")

        # Set all subdirectories to 777
        for d in dirs:
            dir_path = os.path.join(root, d)
            try:
                os.chmod(dir_path, 0o777)
            except Exception as e:
                print(f"Warning: Could not chmod {dir_path}: {e}")

        # Set all files to 666 (rw-rw-rw-)
        for f in files:
            file_path = os.path.join(root, f)
            try:
                os.chmod(file_path, 0o666)
            except Exception as e:
                print(f"Warning: Could not chmod {file_path}: {e}")

    # Make shell scripts executable (755)
    pipelines_dir = job_dir / "pipelines"
    if pipelines_dir.exists():
        for script in pipelines_dir.rglob("*.sh"):
            try:
                script.chmod(0o755)
            except Exception as e:
                print(f"Warning: Could not chmod {script}: {e}")


def _resolve_pipeline_stages(metadata: dict) -> dict:
    """
    Returns a dict of stage names to their initial status.
    
    Example:
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
    """Initialize the state.json file with starting state."""
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
    """Write state to state.json file."""
    state_file = job_dir / "state.json"
    state_file.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    # Make state file readable
    try:
        state_file.chmod(0o666)
    except:
        pass


def _now() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _start_runner_container(job_id: str, metadata: dict):
    """
    Start a Docker container that will execute pipeline stages.
    The container mounts the host workspaces directory.
    """
    image = _select_runner_image(metadata)

    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", f"runner-{job_id}",
            "-u", "10001:10001",  # Run as non-root user

            # Environment variables for pipeline scripts
            "-e", f"APP_DIR=/home/runner/workspaces/{job_id}/source",
            "-e", f"PIPELINES_DIR=/home/runner/workspaces/{job_id}/pipelines",
            "-e", f"REPORTS_DIR=/home/runner/workspaces/{job_id}/reports",

            # Mount host workspaces directory
            "-v", f"{HOST_WORKSPACES_PATH}:/home/runner/workspaces",

            "-w", "/home/runner",
            image,
            "tail", "-f", "/dev/null",  # Keep container running
        ],
        check=True,
    )
    
    # Fix Git safe.directory issue (Git 2.35.2+ security feature)
    # This allows Git to work with repos owned by different users
    subprocess.run(
        [
            "docker", "exec", f"runner-{job_id}",
            "git", "config", "--global", "--add", "safe.directory", 
            f"/home/runner/workspaces/{job_id}/source"
        ],
        check=False,  # Don't fail if git config fails
    )


def _select_runner_image(metadata: dict) -> str:
    """Select the appropriate Docker image based on project stack."""
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
    """Execute a single pipeline stage."""
    state = _read_state(job_dir)

    # Update state → RUNNING
    state["current_stage"] = stage
    state["stages"][stage]["status"] = "RUNNING"
    state["updated_at"] = _now()
    _write_state(job_dir, state)

    # Create stage-specific report directory
    stage_report_dir = job_dir / "reports" / stage.lower()
    stage_report_dir.mkdir(parents=True, exist_ok=True)
    
    # Set permissions on report directory
    try:
        stage_report_dir.chmod(0o777)
    except:
        pass

    # Get the script to execute for this stage
    stage_script = _resolve_stage_script(metadata, stage)

    # Execute the stage script
    # Note: We don't check=True because we want to read the result.json
    # regardless of the script's exit code
    subprocess.run(
        [
            "docker", "exec",
            f"runner-{job_id}",
            "bash", "-lc",
            f'cd "$APP_DIR" && bash {stage_script}',
        ],
        check=False,
    )

    # Special handling for SECRETS stage (normalize output location)
    if stage == "SECRETS":
        subprocess.run(
            [
                "docker", "exec",
                f"runner-{job_id}",
                "bash", "-lc",
                (
                    "mkdir -p $REPORTS_DIR/secrets && "
                    "if [ -f $REPORTS_DIR/secrets-dir/result.json ]; then "
                    "  mv $REPORTS_DIR/secrets-dir/* $REPORTS_DIR/secrets/ && "
                    "  rmdir $REPORTS_DIR/secrets-dir; "
                    "elif [ -f $REPORTS_DIR/secrets-git/result.json ]; then "
                    "  mv $REPORTS_DIR/secrets-git/* $REPORTS_DIR/secrets/ && "
                    "  rmdir $REPORTS_DIR/secrets-git; "
                    "fi"
                ),
            ],
            check=True,
        )

    # Read the stage result
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

    # Handle stage success
    if result["status"] == "SUCCESS":
        state["stages"][stage]["status"] = "SUCCESS"
        state["updated_at"] = _now()
        _write_state(job_dir, state)
        return

    # Handle stage failure
    state["stages"][stage]["status"] = "FAILED"
    state["updated_at"] = _now()

    # Check if this is a blocking stage
    if stage in BLOCKING_STAGES:
        state["state"] = "FAILED"
        state["error"] = result.get("message", "blocking stage failed")
        _write_state(job_dir, state)
        raise RuntimeError(f"Blocking stage {stage} failed")

    # Non-blocking failure → log warning and continue pipeline
    state.setdefault("warnings", {})
    state["warnings"][stage] = result.get("message", "stage failed")
    _write_state(job_dir, state)


def _read_state(job_dir: Path) -> dict:
    """Read current state from state.json."""
    return json.loads((job_dir / "state.json").read_text())


def _resolve_stage_script(metadata: dict, stage: str) -> str:
    """Get the path to the script for a given stage."""
    if stage == "SECRETS":
        pipeline = metadata.get("pipeline", {})
        mode = pipeline.get("secret_scan_mode", "dir")

        script = SECRETS_SCRIPT_BY_MODE.get(mode)
        if not script:
            raise RuntimeError(f"Unsupported secret scan mode: {mode}")

        return f"$PIPELINES_DIR/global/{script}"

    # For other stages, use framework-specific scripts
    pipeline_dir = _resolve_pipeline_dir(metadata)
    return f"$PIPELINES_DIR/{pipeline_dir}/{stage.lower()}.sh"


def _resolve_pipeline_dir(metadata: dict) -> str:
    """Determine the pipeline directory based on framework and build tool."""
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
    """Update final job state."""
    state = _read_state(job_dir)
    state["state"] = "SUCCEEDED" if success else "FAILED"
    state["current_stage"] = None
    state["updated_at"] = _now()

    if error:
        state["error"] = error

    _write_state(job_dir, state)


def _stop_runner_container(job_id: str):
    """Stop and remove the runner container."""
    subprocess.run(
        ["docker", "rm", "-f", f"runner-{job_id}"],
        check=False,
    )