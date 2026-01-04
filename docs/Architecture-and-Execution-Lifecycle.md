# Deployment & Infrastructure Layer (Docker Compose Topology)

The deployment is build around **3-service Docker Compose stack** :

- **backend** → FastAPI API server (job intake + orchestration)
- **worker** → Celery worker (runs long pipeline jobs asynchronously)
- **redis** → message broker + results backend for Celery

## docker-compose.yml: What runs, and why

### Service: `redis`

```bash
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```

**Role**

- Redis is the **single coordination point** between backend and worker:
    - Celery uses it as the **broker** (queue) and **backend** (task results).
- In `celery_app.py`, this is hardwired as:
    - broker: `redis://redis:6379/0`
    - backend: `redis://redis:6379/1`

### Service: `backend` (FastAPI)

```bash
backend:
  build:
    context: .
    dockerfile: backend/Dockerfile
  container_name: pipelinex-backend
  volumes:
    - workspaces:/workspaces
    - /var/run/docker.sock:/var/run/docker.sock
  ports:
    - "8000:8000"
  depends_on:
    - redis
```

**Critical mounts**

1-`workspaces:/workspaces`

- This is the shared persistent area where job files live.
- Backend creates workspaces here (job directories).
- Worker reads the same directories later to execute jobs.
- This is what makes the system “two-process” safe: API and worker don’t need to run in the same container.

2-`/var/run/docker.sock:/var/run/docker.sock`

- it gives the backend container access to the **host Docker engine**.
- That lets the code run commands like:
    - `docker run ...` (runner containers)
    - `docker volume rm ...` (cleanup reports volume)

Without this mount, the backend/worker could not start the runner container that actually runs Maven + security tools.

**depends_on**

- Ensures Redis container is started before backend starts.

### Service: `worker` (Celery)

```bash
worker:
  build:
    context: .
    dockerfile: backend/Dockerfile
  container_name: pipelinex-worker
  command: celery -A celery_app.celery_app worker --loglevel=info
  volumes:
    - workspaces:/workspaces
    - /var/run/docker.sock:/var/run/docker.sock
  depends_on:
    - redis
```

**Role**

- Runs the `execute_job (job_execution.py)` task asynchronously.
- Pulls jobs from Redis, reads workspace metadata, runs the pipeline, updates state, writes reports.

**Same image as backend**

- Both backend and worker are built from the same `backend/Dockerfile`.
- This is common in distributed Python apps:
    - backend runs `uvicorn ...`
    - worker runs `celery ...`

**Same mounts**

- Must mount `workspaces` because it needs to read job files (`metadata.json`, pipelines, source).
- Must mount docker.sock because it launches the runner container and manages volumes.

## Named volume: `workspaces`

```bash
volumes:
  workspaces:
```

**What it provides**

- Persistent storage managed by Docker.
- Shared between backend and worker containers.
- Survives container restarts (unless you remove the volume).

**Why this matters**

- A job’s entire lifecycle depends on a shared directory:
    - Backend writes: source code, installed pipeline scripts, metadata
    - Worker reads: metadata, pipeline scripts, and runs the job
    - Worker writes: state.json updates + artifacts

## Backend/Dockerfile: What the image contains

```bash
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    docker.io \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/backend

COPY backend/ .
COPY pipelines/ /workspace/pipelines/

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Installed OS packages

- **git**: required for cloning GitHub repos inside the container (repo input path).
- **docker.io**: installs Docker CLI so the container can run `docker run`, `docker volume rm`, etc.
    - This works *because* we mount `/var/run/docker.sock`, i.e., the CLI talks to the host Docker daemon.
- **curl + ca-certificates**: common for health checks, downloads, TLS connectivity, etc.

### File layout inside the container

- Backend code ends up at: `/workspace/backend/...`
- Pipelines copied into image at: `/workspace/pipelines/...`

### One image, two roles

- Backend container uses Dockerfile’s `CMD` → runs FastAPI via Uvicorn.
- Worker overrides command in compose → runs Celery worker.

This avoids maintaining two separate images.

## Storage model for reports

Even though Compose defines only one named volume (`workspaces`), the worker creates **additional named volumes per job**:

- `reports-<job_id>`

These are not declared in docker-compose.yml, but Docker allows volumes to be created implicitly when a container references them.

**Lifecycle**

- Created/used during job execution
- Ownership adjusted via a temporary `busybox` container


# End-to-end request lifecycle overview (ZIP/GitHub → queue → runner → reports)

## Actors and components involved

### Client

- Sends either:
    - a ZIP file upload + metadata (multipart form)
    
    ```json
    {
      "stack": {
        "language": "java",
        "framework": "spring-boot",
        "build_tool": "maven"
      },
      "versions": {
        "java": "17",
        "build_tool": "3.9"
      },
      "pipeline": {
        "run_build": true,
        "run_unit_tests": true,
        "run_sast": true,
        "run_sca": true,
        "run_secret_scan": true
      }
    }
    ```
    
    - a GitHub repo URL + metadata (JSON).
    
    ```json
    {
      "github_url": "https://github.com/ABDERRAHMANE2303/math-lab.git",
      "stack": {
        "language": "java",
        "framework": "spring-boot",
        "build_tool": "maven"
      },
      "versions": {
        "java": "17",
        "build_tool": "3.9"
      },
      "pipeline": {
        "run_build": true,
        "run_unit_tests": true,
        "run_sast": true,
        "run_sca": true,
        "run_secret_scan": true
      }
    }
    ```
    

### Backend container (FastAPI)

- Receives the request.
- Creates a workspace.
- Validates the project structure (job admission).
- Installs the correct pipeline scripts into the workspace.
- Enqueues an async task to the worker.

### Redis container

- Acts as **Celery broker** (task queue) and **results backend**.

### Worker container (Celery)

- Picks up the queued job.
- Reads job metadata.
- Launches a separate runner container to execute pipeline scripts.
- Produces state and reports.

### Runner container (per job, launched dynamically)

- The actual execution environment (Java + Maven image for now).
- Runs your pipeline scripts (build/test/etc.) against the project source.

### Storage

- `workspaces` volume: shared job workspace (source + pipelines + metadata + state).
- `reports-<job_id>` volume: reports output volume (JSON + logs from pipeline stages).

## Common job artifacts (files & directories)

### Workspace directory : `/workspaces/<job_id>/`

Contains:

- `source/` → the project code (unzipped or cloned)
- `pipelines/` → copied pipeline scripts for this job
- `metadata.json` → full job config and admission result
- `state.json` → execution state written by the worker

### Reports directory (inside the reports volume)

Mounted inside runner at:

- `/home/runner/reports`

## 1-ZIP/GitHub : request → job created

### Step 1 — Client request

`POST /api/jobs/upload`

`POST /api/jobs/github` 

### Step 2 — Backend apply security checks, validate structure and create workspace

Api calls JobOrchestrator 

JobOrchestrator calls `handle_zip_input` or `clone_github_repository`

If `handle_zip_input` or `clone_github_repository` fails, no job is created.

## 2-admission → pipeline install → enqueue

### Step 1 — Job admission (structure validation + metadata.json)

JobOrchestrator calls:

- `admit_job(workspace, stack, versions, pipeline)`

Results:

- `metadata.json` written into the job directory ( and also returned as a response to the user request)
- Execution state starts as `"QUEUED"` in metadata.
- If admission fails, the workspace is removed.

### Step 2 — Pipeline installation into the workspace

JobOrchestrator calls:

- `install_pipelines(workspace, "spring-boot-maven")` (currently hardcoded)

Effect:

- Copies pipeline scripts into:
    - `<job_dir>/pipelines/spring-boot-maven/`
- This makes the pipeline self-contained inside the workspace.
- If pipeline installation fails, workspace is removed.

### Step 3 — Queue the job for async execution

JobOrchestrator calls:

- `execute_job.delay(workspace.job_id)`

This means:

- A Celery task message goes into Redis queue.
- Backend finishes quickly and stays responsive.
- If dispatch fails, workspace is removed.

## 3-Worker execution: queued job → running job

### Step 1 — Worker receives the task

Celery worker picks up:

- `execute_job(job_id)`

### Step 2 — Worker loads metadata and marks state RUNNING

Worker reads:

- `<job_dir>/metadata.json`

Then writes:

- `<job_dir>/state.json` = `{ "state": "RUNNING" }`

This “state.json” becomes the single source of truth for live execution status. ( "execution_state" inside metedata.json is always"QUEUED”, as of now no code update it)

## 4-Preparing execution: permissions + reports volume

Before launching the runner container, worker ensures the environment is safe and writable.

### Step 1 — Fix workspace permissions

Worker runs:

- `chown -R 10001:10001 <job_dir>`
- `chmod -R u+rwx <job_dir>`
- marks pipeline scripts executable

Reason:

- Runner container runs as UID 10001.
- The workspace volume must be writable by the same UID to avoid permission failures.

### Step 2 — Initialize reports volume ownership

Worker ensures Docker named volume:

- `reports-<job_id>`

is writable by UID 10001 using a tiny helper container.

This is necessary because Docker volumes often start owned by root.

## 5-Runner execution: running pipeline scripts in an isolated container

### Step 1 — Select a runner image

Worker chooses image based on metadata stack:

- Java + Maven → `abderrahmane03/pipelinex:java17-mvn3.9.12-latest`

(Other stacks would raise an error currently.)

### Step 2 — Launch runner container (docker run)

The worker runs a Docker container with:

**Environment variables**

- `APP_DIR` points to the job’s source code inside the mounted workspace
- `PIPELINES_DIR` points to the job’s pipelines folder
- `REPORTS_DIR` points to reports mount

**Mounts**

- `securedevops_workspaces:/home/runner/workspaces`
    - makes the workspace visible to runner
- `reports-<job_id>:/home/runner/reports`
    - where scripts write results/logs

**Working directory**

- `/home/runner`

**Command**

- `bash -c "<pipeline command>"`

The “pipeline command” is a chain like:

- BUILD → `build.sh`
- TEST → `test.sh`
- SAST / SCA / SECRETS based on toggles

Each stage is wrapped with log markers:

- `[PIPELINE] START ...`
- `[PIPELINE] END ...`

If any stage fails, the `&&` chain stops immediately and the container exits non-zero.

## 6-Reports production: what a stage outputs

Each pipeline stage follows the same pattern (example: `build.sh`):

- creates a stage directory inside `REPORTS_DIR`
- writes:
    - `result.json` (machine-readable summary)
    - `<stage>.log` (full stdout/stderr)

So after execution, you have:

- structured results for dashboards/automation
- raw logs for debugging

## 7-Completion: success or failure state

### Success

Worker writes:

- `state.json` → `{ "state": "SUCCEEDED" }`

### Failure

If anything fails:

- worker catches exception
- writes:
    - `state.json` → `{ "state": "FAILED", "error": "<message>" }`
- re-raises so Celery records failure too

This gives you **two layers** of status:

- internal Celery task status
- your own file-based `state.json` status for consumers