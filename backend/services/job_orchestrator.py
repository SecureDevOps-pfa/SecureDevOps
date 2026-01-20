from services.workspace_service import cleanup_workspace
from services.zip_input_service import handle_zip_input
from services.repo_input_service import clone_github_repository
from services.job_admission import admit_job
from services.pipeline_installer import install_pipelines
from tasks.job_execution import execute_job
from config import DEFAULT_DATABASE_CONFIG

class JobOrchestrator:
    """
    Central authority for job admission.
    Workspace lifecycle is delegated to workspace_service.
    """

    def _inject_database_config(self, metadata: dict) -> dict:
        """
        Inject static database configuration if the stack requires a DB.
        """
        stack = metadata.get("stack", {})

        if stack.get("requires_db"):
            metadata["database"] = DEFAULT_DATABASE_CONFIG.copy()
        else:
            metadata["database"] = None

        return metadata

    def create_job_from_zip_input(self, *, file, metadata: dict):
        workspace = None

        try:
            workspace = handle_zip_input(file)

            metadata = self._inject_database_config(metadata)
            job_metadata = admit_job(
                workspace=workspace,
                stack=metadata["stack"],
                versions=metadata.get("versions", {}),
                pipeline=metadata["pipeline"],
                database=metadata["database"],
            )
            
            framework = "spring-boot-maven"  # hardcoded for now
            install_pipelines(workspace, framework)

            execute_job.delay(workspace.job_id)

            return job_metadata

        except Exception:
            if workspace:
                cleanup_workspace(workspace)
            raise

    def create_job_from_repo_input(self, *, github_url: str, metadata: dict):
        workspace = None

        try:
            pipeline = metadata["pipeline"]
            run_secret_scan = pipeline.get("run_secret_scan", False)
            secret_scan_mode = pipeline.get("secret_scan_mode", "dir")

            keep_git = run_secret_scan and secret_scan_mode == "git"
            full_history = keep_git

            workspace = clone_github_repository(
                github_url,
                keep_git=keep_git,
                full_history=full_history,
            )

            metadata = self._inject_database_config(metadata)
            job_metadata = admit_job(
                workspace=workspace,
                stack=metadata["stack"],
                versions=metadata.get("versions", {}),
                pipeline=metadata["pipeline"],
                database=metadata["database"],
            )

            framework = "spring-boot-maven"  # hardcoded for now
            install_pipelines(workspace, framework)

            execute_job.delay(workspace.job_id)
            return job_metadata

        except Exception:
            if workspace:
                cleanup_workspace(workspace)
            raise
