```bash
SecureDevOps/
├── README.md
├── docker-compose.yml
│
├── backend/
│   ├── Dockerfile
│   ├── app.py
│   ├── celery_app.py
│   ├── config.py
│   ├── requirements.txt
│   │
│   ├── contracts/
│   │   └── spring-boot-maven.json
│   │
│   ├── services/
│   │   ├── job_admission.py
│   │   ├── job_orchestrator.py
│   │   ├── pipeline_installer.py
│   │   ├── repo_input_service.py
│   │   ├── workspace_service.py
│   │   └── zip_input_service.py
│   │
│   ├── tasks/
│   │   └── job_execution.py
│   │
│   ├── tests/
│   │   ├── api.http
│   │   └── fixtures/
│   │
│   ├── utils/
│   │   ├── content_safety.py
│   │   ├── repo_safety.py
│   │   └── zip_safety.py
│   │
│   └── validators/
│       └── structure_validator.py 

│
├── pipelines/
│   └── spring-boot-maven/
│       ├── build.sh
│       ├── dast.sh
│       ├── package.sh
│       ├── sast.sh
│       ├── sca.sh
│       ├── secrets.sh
│       ├── smoke.sh
│       └── test.sh
│
└── runners/
    ├── java17-gradle/
    │   └── Dockerfile
    └── java17-maven3.9/
        └── Dockerfile
```

1. **API entry layer (`app.py`)**
    
    `app.py` is the **public entry point** of the system. It exposes HTTP endpoints that:
    
    1. accept a project input (ZIP upload or GitHub URL),
    2. validate request format,
    3. delegate the real work to the orchestration layer (`JobOrchestrator`),
    4. return a **job metadata response immediately** (execution happens asynchronously).
2. **Orchestration layer (`job_orchestrator.py`)**
    
    `JobOrchestrator` is the **bridge** between:
    
    - the API layer (incoming request),
    - workspace + ingestion services,
    - admission/validation,
    - pipeline installation,
    - and async execution scheduling.
    
    It enforces a strict lifecycle:
    
    1. create workspace
    2. fill workspace with source
    3. validate/admit job & persist metadata
    4. install pipelines into workspace
    5. enqueue background execution
    6. cleanup on failure
3. **Input ingestion**
    - GitHub path (`repo_input_service.py`)
    - ZIP path (`zip_input_service.py`)
    
    → both calls `create_workspace()` (which returns workspace ) and in case of failure they call `cleanup_workspace`
    
4. **Workspace management (`workspace_service.py`)**
    1. The Workspace data model
        
        ```python
        @dataclass
        class Workspace:
            job_id: str
            job_dir: Path
            source_dir: Path
        ```
        
        - `job_id`: the identifier used everywhere (API response, metadata, Celery task argument)
        - `job_dir`: root folder for the job (ex: `/workspaces/job-001`)
        - `source_dir`: location of checked-out/unzipped source code (ex: `/workspaces/job-001/source`)
    2. Job ID generation strategy `_generate_job_id()`
        - Ensures the workspaces root exists.
        - Counts existing directories matching `job-*`.
        - Generates the next ID in a simple increasing sequence:
            - job-001, job-002, job-003, ...
    3. Workspace directory layout `create_workspace()`
        
        ```bash
        /workspaces/job-XYZ/
          source/
          pipelines/
        ```
        
    4. Workspace cleanup `cleanup_workspace`
        
        Cleanup is invoked primarily on failures during job intake/orchestration:
        
        - ZIP extraction errors
        - git clone errors
        - admission errors
        - pipeline installation errors
5. **Job admission (`job_admission.py`) + the Spring Boot Maven contract**
    1. After the workspace is created and filled with source code, Orchestrator calls `admit_job()` 
        
        ```python
        def admit_job(*, workspace: Workspace, stack: dict, versions: dict, pipeline: dict):
            contract = Path("contracts/spring-boot-maven.json")
        
            validation = validate_structure(workspace.source_dir, contract)
        
            if validation.status == "REFUSED":
                raise ValueError(validation.errors)
        ```
        
    2. `validate_structure(workspace.source_dir, contract)` inspects the extracted/cloned project content.
        1. The Spring Boot Maven contract (`spring-boot-maven.json`)
        
        ```json
        {
          "required_paths": [
            "pom.xml",
            "src/main/java"
          ],
          "required_files": [
            {
              "pattern": "**/*.java",
              "min_count": 1
            }
          ],
          "semantic_checks": [
            {
              "type": "contains_text",
              "value": "@SpringBootApplication",
              "exactly_one": true
            }
          ],
          "optional_paths": [
            "src/test/java"
          ]
        }
        ```
        
        The project must contain:
        
        - `pom.xml`→ proof it’s a Maven project and defines dependencies/build lifecycle
        - `src/main/java`→ standard Maven directory for Java production source
        - There must be at least: one `.java` file anywhere in the project tree.
        - The project must contain the text: `@SpringBootApplication` → 
        checks the project is *actually* Spring Boot.
        - If `src/test/java` exists: tests are present
    3. Metadata generation
        
        ```python
        metadata = {
            "job_id": workspace.job_id,
            "status": validation.status,
            "execution_state": "QUEUED",
            "stack": stack,
            "versions": versions,
            "pipeline": pipeline,
            "warnings": validation.warnings,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        ```
        
    4. Persistence: writing `metadata.json`
        
        ```python
        (workspace.job_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )
        ```
        
6. **Pipeline installation (`pipeline_installer.py`)**
    1. After a job is admitted, we need to ensure the job has a **self-contained copy of the pipeline scripts** it will execute. That’s exactly what `pipeline_installer.py` does.
    2. Installation function behavior
        
        ```python
        def install_pipelines(workspace: Workspace, framework: str):
            src = PIPELINES_ROOT / framework
            dst = workspace.job_dir / "pipelines" / framework
        ```
        
        **Source path (`src`)**
        
        - Example: `<repo_root>/pipelines/spring-boot-maven`
        
        **Destination path (`dst`)**
        
        - Example: `/workspaces/job-001/pipelines/spring-boot-maven`
    3. fail early if pipeline missing
        
        ```python
        if not src.exists():
            raise RuntimeError(f"Pipelines not found for framework: {framework}")
        ```
        
    4. Idempotency: re-installation handling
        
        ```python
        if dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
        ```
        
        This makes pipeline installation *safe to re-run* for the same job directory.
        
        Why it matters:
        
        - if the job is recreated or re-admitted
        - if pipeline install is retried after partial failure
        - it prevents mixing old and new scripts
        
        ```python
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
        ```
        
        - Ensures `<job_dir>/pipelines/` exists
        - Copies the full pipeline directory (all scripts, configs, etc.)
7. **Async execution dispatch (Celery config + `.delay()`)**
    1. Instead of making the HTTP request wait for build/scans, the backend enqueues a task and returns immediately, while a worker consumes and executes jobs in the background.
    2. The async system has 3 pieces:
        1. In `job_orchestrator.py`, after: workspace ingestion, admission (`metadata.json` written), pipeline installation, `job_orchestrator` calls `.delay(job_id)` to enqueue work
            
            ```python
            execute_job.delay(workspace.job_id)
            ```
            
            `.delay(...)` is Celery’s convenient shortcut for:
            
            - creating a task message
            - serializing arguments (`job_id`)
            - sending the message to the broker (Redis)
        2. **Redis** stores the task message and task result state
        3. **Celery worker** pulls tasks and runs `execute_job(job_id)`
    3. Celery application setup (`celery_app.py`)
        
        ```python
        celery_app = Celery(
            "pipelinex",
            broker="redis://redis:6379/0",
            backend="redis://redis:6379/1",
        )
        ```
        
        - **App name: `"pipelinex"`**
            - Celery uses this as an identifier for:
                - worker naming
                - task routing namespace
                - logs/monitoring tools
        - **Broker: `redis://redis:6379/0`**
            - The broker is where tasks are queued.
            - Database index `/0` is used for queue messages.
        - **Backend: `redis://redis:6379/1`**
            - The results backend stores:
                - task state (`PENDING`, `STARTED`, `FAILURE`, `SUCCESS`, etc.)
                - task return values
            - Using a different Redis DB index (`/1`) keeps queues and results logically separated.
    4. Environment-driven worker execution model
        
        ```python
        def get_worker_pool():
            return os.getenv("CELERY_WORKER_POOL", "prefork")
        
        def get_concurrency():
            return int(os.getenv("CELERY_WORKER_CONCURRENCY", "1"))
        ```
        
        - `worker_pool`
            - Default: `"prefork"`
            - Meaning: Celery forks worker processes.
            - This is the classic Celery model and works well for CPU-bound tasks.
        - `worker_concurrency`
            - Default: `1`
            - Meaning: only one task runs at a time in this worker container.
        - **How to scale**
            
            We have two knobs:
            
            1. run more worker containers (`docker compose up --scale worker=3`)
            2. increase concurrency per worker (`CELERY_WORKER_CONCURRENCY=2`)
    5. Serialization, content acceptance and Timezone settings
        
        ```python
        celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
        		enable_utc=True,
        )
        ```
        
    6. Reliability settings for long-running jobs
        
        ```python
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        ```
        
        - `task_acks_late=True`
            - Celery acknowledges a task **after it has executed**, not as soon as it is received.
            - Why this matters:
                - If a worker crashes mid-job, the task is not lost.
                - The broker can re-deliver it to another worker
        - `worker_prefetch_multiplier=1`
            - Each worker process only “pre-fetches” 1 task at a time.
            - Why this matters:
                - Prevents one worker from reserving many tasks and starving others.
                - Better fairness when tasks have very different runtimes (build might take 30s; scanning might take 10m).
    7. Task discovery (how Celery learns about `execute_job`)
        
        ```python
        import tasks.job_execution
        ```
        
        when the worker starts:
        
        - Python imports the module
        - the `@celery_app.task(...)` decorator runs
        - the `execute_job` task gets registered
8. **Worker execution (`tasks/job_execution.py`)**
    1. Task registration and signature
        
        ```python
        @celery_app.task(bind=True, name="execute_job")
        def execute_job(self, job_id: str):
        ```
        
        - `name="execute_job"`: the task is registered under this exact string. This matches what’s enqueued by `.delay()`.
        - `bind=True`: passes the task instance as `self`, which allows:
            - access to retry methods (`self.retry(...)`) if we later add them
            - access to request context / task metadata
        - The task argument is only `job_id`.:
            - all other job information is on disk (`metadata.json`) inside the workspace.
    2. Workspace lookup and metadata loading
        
        ```python
        job_dir = WORKSPACES_DIR / job_id
        metadata = json.loads((job_dir / "metadata.json").read_text())
        ```
        
        - The worker expects a deterministic directory layout:
            - `/workspaces/job-XYZ/metadata.json`
        - `metadata.json` becomes the single source of truth for:
            - stack selection
            - pipeline toggles
    3. State transition: RUNNING
        
        ```python
        _update_execution_state(job_dir, "RUNNING")
        ```
        
        This writes:
        
        - `<job_dir>/state.json`
        
        Example output:
        
        ```json
        {
        "state":"RUNNING"
        }
        ```
        
    4. Main execution try/except
        
        ```python
        try:
            _prepare_workspace_permissions(job_dir)
            _init_reports_volume(metadata["job_id"])
            _run_runner_container(job_dir, metadata)
            _update_execution_state(job_dir, "SUCCEEDED")
        
        except Exception as exc:
            _update_execution_state(job_dir, "FAILED", str(exc))
            raise
        ```
        
        - Guarantee A — State is always updated
            - On success: `SUCCEEDED`
            - On failure: `FAILED` with an error message
        - Guarantee B — Errors propagate:
            - Celery records the task as failed in Redis backend
            - Logs show the stack trace
    5. Workspace permissions preparation `_prepare_workspace_permissions(job_dir)` :
        
        ```python
        subprocess.run(["chown", "-R", "10001:10001", str(job_dir)], check=True)
        subprocess.run(["chmod", "-R", "u+rwx", str(job_dir)], check=True)
        ```
        
        The runner container is started with: `"-u", "10001:10001"` , so inside the runner, processes run as user 10001 (non-root).
        
        The workspace volume files are owned by root, runner scripts may fail when they try to:
        
        - write build outputs
        - create temporary files
        - write reports
        - chmod scripts
        
        ```python
        pipelines_dir = job_dir / "pipelines"
        if pipelines_dir.exists():
            for script in pipelines_dir.glob("*.sh"):
                script.chmod(0o755)
        ```
        
        - Ensure pipeline scripts are executable.
    6. Reports volume initialization `_init_reports_volume` 
        
        ```python
        def _init_reports_volume(job_id: str):
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
        ```
        
        - Creates or attaches the named volume: `reports-job-XYZ`
        - Runs a temporary `busybox` container that:
            - mounts the volume at `/home/runner/reports`
            - changes ownership to `10001:10001`
    7. Runner container execution `_run_runner_container` 
        1. Runner image selection `_select_runner_image` :
            
            ```python
            if stack.get("language") == "java" and stack.get("build_tool") == "maven":
                return "abderrahmane03/pipelinex:java17-mvn3.9.12-latest"
            raise RuntimeError("Unsupported stack for runner selection")
            ```
            
            This is currently a strict mapping:
            
            - Only Java + Maven jobs can run.
            - Everything else is refused at runtime (ideally you’d refuse earlier, but this still protects execution).
        2. docker run command breakdown 
            
            ```python
            subprocess.run(
              [
                "docker", "run", "--rm",
                "-u", "10001:10001",
            
                "-e", f"APP_DIR=/home/runner/workspaces/{job_id}/source",
                "-e", f"PIPELINES_DIR=/home/runner/workspaces/{job_id}/pipelines",
                "-e", "REPORTS_DIR=/home/runner/reports",
            
                "-v", "securedevops_workspaces:/home/runner/workspaces",
                "-v", f"reports-{job_id}:/home/runner/reports",
            
                "-w", "/home/runner",
                image,
                "bash", "-c", _pipeline_command(metadata),
              ],
              check=True
            )
            
            ```
            
            - `-rm`: container is deleted immediately after it exits (stateless execution).
            - `u 10001:10001`: non-root execution (better security posture).
            - `APP_DIR`: where the application source code is inside runner.
            - `PIPELINES_DIR`: where pipeline scripts are inside runner.
            - `REPORTS_DIR`: where scripts write results/logs.
            - Workspaces mount: `"securedevops_workspaces:/home/runner/workspaces"` (we give access to the job workspace created by backend. )
        3. Pipeline command `_pipeline_command` :
            - Pipeline directory resolution `_resolve_pipeline_dir` :
                
                ```python
                framework = stack.get("framework")
                build_tool = stack.get("build_tool")
                return f"{framework}-{build_tool}"
                ```
                
                For a Spring Boot Maven project:
                
                - framework = `spring-boot`
                - build_tool = `maven`
                - pipeline folder = `spring-boot-mave`
                - So the base script folder becomes:
                    - `$PIPELINES_DIR/spring-boot-mave`
            - Stage selection based on metadata.json
                
                ```python
                if pipeline.get("run_build", True): ...
                if pipeline.get("run_unit_tests", True): ...
                if pipeline.get("run_sast", False): ...
                ...
                ```
                
            - Pipeline command composition:
                
                ```python
                return " && ".join(commands)
                ```
                
                The pipeline is executed as one chained shell command with `&&`, meaning:
                
                - each stage runs only if the previous stage succeeded
                - the first failure stops the pipeline immediately
                - the runner container exits non-zero
                - Celery task catches exception and marks job FAILED