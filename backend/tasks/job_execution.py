import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Optional

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
            stage: {
                "status": status,
                "message": None
            }
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
    state["stages"][stage]["message"] = None
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
    
    topology = resolve_topology(stage, metadata)

    if needs_compose(topology):
        _run_dynamic_compose(
            job_dir=job_dir,
            job_id=job_id,
            metadata=metadata,
            stage=stage,
            topology=topology,
        )

        # DAST still produces result.json on filesystem
        result_path = job_dir / "reports" / stage.lower() / "result.json"
        if not result_path.exists():
            raise RuntimeError(f"{stage} did not produce reports/{stage.lower()}/result.json")

        result = json.loads(result_path.read_text(encoding="utf-8"))
    else :
        stage_script = _resolve_stage_script(metadata, stage)

        env_exports = []

        pipeline = metadata.get("pipeline", {})

        # Inject custom vars if needed
        if stage == "SECRETS" and pipeline.get("secret_scan_mode") == "custom":
            custom = pipeline.get("secret_custom", {})
            env_exports = [
                f'export STAGE="{stage}"',
                f'export INSTALL_CMD="{custom["install_cmd"]}"',
                f'export TOOL_CMD="{custom["tool_cmd"]}"',
                f'export LOG_EXT=".{custom.get("log_ext", "json")}"',
            ]

        if stage == "SAST" and pipeline.get("sast_mode") == "custom":
            custom = pipeline.get("sast_custom", {})
            env_exports = [
                f'export STAGE="{stage}"',
                f'export INSTALL_CMD="{custom["install_cmd"]}"',
                f'export TOOL_CMD="{custom["tool_cmd"]}"',
                f'export LOG_EXT=".{custom.get("log_ext", "json")}"',
            ]

        env_prefix = " && ".join(env_exports)

        cmd = (
            f'{env_prefix} && cd "$APP_DIR" && bash {stage_script}'
            if env_exports
            else f'cd "$APP_DIR" && bash {stage_script}'
        )

        subprocess.run(
            [
                "docker", "exec",
                f"runner-{job_id}",
                "bash", "-lc",
                cmd,
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

    stage_status = result.get("status", "FAILURE")
    stage_message = result.get("message")

    state["stages"][stage]["status"] = stage_status
    state["stages"][stage]["message"] = stage_message
    state["updated_at"] = _now()
    _write_state(job_dir, state)

    # Stop pipeline  on blocking stage
    if stage_status == "FAILURE" and stage in BLOCKING_STAGES:
        state["state"] = "FAILED"
        state["error"] = stage_message or f"{stage} failed"
        _write_state(job_dir, state)
        raise RuntimeError(f"Blocking stage {stage} failed")


def _read_state(job_dir: Path) -> dict:
    """Read current state from state.json."""
    return json.loads((job_dir / "state.json").read_text())

def _run_dynamic_compose(
    *,
    job_dir: Path,
    job_id: str,
    metadata: dict,
    stage: str,
    topology: dict,
):
    """
    Runs a dynamically assembled docker-compose based on topology.
    Currently supports:
      - app
      - app + db
      - app + zap
      - app + db + zap
    """

    compose_root = _repo_root() / "runners" / "compose"
    if not compose_root.exists():
        raise RuntimeError("compose templates directory not found")

    compose_files = select_compose_files(stage, topology)

    # Copy compose fragments into job workspace
    copied_files = []
    for name in compose_files:
        src = compose_root / name
        if not src.exists():
            raise RuntimeError(f"Compose fragment not found: {src}")

        dst = job_dir / name
        shutil.copyfile(src, dst)
        copied_files.append(dst)

    port = "8080"
    network = f"pipelinex-net-{job_id}"

    env = os.environ.copy()
    
    # ------------------------------------------------------------------
    # Inject database configuration (if required)
    # ------------------------------------------------------------------
    if topology.get("db"):
        db = metadata.get("database")
        if not db:
            raise RuntimeError(
                "Topology requires database but no database configuration found in metadata"
            )

        env.update({
            "DB_IMAGE": db.get("image", "postgres:15"),
            "DB_NAME": db.get("name", "app"),
            "DB_USER": db.get("user", "postgres"),
            "DB_PASSWORD": db.get("password", "postgres"),
            "DB_PORT": str(db.get("port", 5432)),
            "DB_DRIVER": db.get("driver", "postgresql"),
        })

    env.update({
        "JOB_ID": job_id,
        "PORT": port,
        "DOCKER_NETWORK": network,
        "HOST_WORKSPACES_PATH": HOST_WORKSPACES_PATH,
        "APP_IMAGE": _select_runner_image(metadata),
    })

    # Inject SCRIPT for app-runner based stages
    if stage != "DAST":
        env["SCRIPT"] = f"/home/runner/pipelines/{_resolve_pipeline_dir(metadata)}/{stage.lower()}.sh"

    compose_cmd = _docker_compose_base_cmd()

    up_cmd = compose_cmd + sum(
        [["-f", str(f)] for f in copied_files],
        []
    ) + [
        "up",
        "--abort-on-container-exit",
        "--exit-code-from", "zap" if topology["zap"] else "app",
    ]

    down_cmd = compose_cmd + sum(
        [["-f", str(f)] for f in copied_files],
        []
    ) + [
        "down",
        "-v",
        "--remove-orphans",
    ]

    try:
        subprocess.run(up_cmd, cwd=str(job_dir), env=env, check=False)
    finally:
        subprocess.run(down_cmd, cwd=str(job_dir), env=env, check=False)

    # Ensure report permissions
    report_dir = job_dir / "reports" / stage.lower()
    if report_dir.exists():
        try:
            report_dir.chmod(0o777)
        except:
            pass

def _repo_root() -> Path:
    # backend/tasks/job_execution.py -> parents[2] == repo root
    return Path(__file__).resolve().parents[2]

def _docker_compose_base_cmd() -> list[str]:
    """
    Prefer 'docker compose'. Fallback to 'docker-compose' if needed.
    """
    try:
        subprocess.run(["docker", "compose", "version"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ["docker", "compose"]
    except Exception:
        # fallback (older setups)
        return ["docker-compose"]

def _resolve_stage_script(metadata: dict, stage: str) -> str:
    pipeline = metadata.get("pipeline", {})

    # -------------------------------
    # SECRETS
    # -------------------------------
    if stage == "SECRETS":
        mode = pipeline.get("secret_scan_mode", "dir")

        if mode == "custom":
            return "$PIPELINES_DIR/global/custom.sh"

        script = SECRETS_SCRIPT_BY_MODE.get(mode)
        if not script:
            raise RuntimeError(f"Unsupported secret scan mode: {mode}")

        return f"$PIPELINES_DIR/global/{script}"

    # -------------------------------
    # SAST
    # -------------------------------
    if stage == "SAST":
        mode = pipeline.get("sast_mode", "default")

        if mode == "custom":
            return "$PIPELINES_DIR/global/custom.sh"

    # -------------------------------
    # All other stages (unchanged)
    # -------------------------------
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

def resolve_topology(stage: str, metadata: dict) -> dict:
    """
    Returns which services are required for this stage.
    """
    topology = {
        "app": True,
        "db": False,
        "zap": False,
    }

    if stage == "SMOKE-TEST":
        topology["db"] = metadata.get("stack", {}).get("requires_db", False)

    if stage == "DAST":
        topology["zap"] = True
        topology["db"] = metadata.get("stack", {}).get("requires_db", False)

    if topology["zap"] and not topology["app"]:
        raise RuntimeError("Invalid topology: zap requires app")

    if topology["db"] and not topology["app"]:
        raise RuntimeError("Invalid topology: db requires app")

    return topology

def needs_compose(topology: dict) -> bool:
    return topology["db"] or topology["zap"]

def select_compose_files(stage: str, topology: dict) -> list[str]:
    files = ["base.yml"]

    if stage == "DAST":
        files.append("app-jar.yml")
    else:
        files.append("app-runner.yml")

    if topology["db"]:
        files.extend(["db.yml", "app-db.yml"])

    if topology["zap"]:
        files.extend(["zap.yml", "app-zap.yml"])

    if topology["db"] and topology["zap"]:
        files.append("app-db-zap.yml")

    return files
