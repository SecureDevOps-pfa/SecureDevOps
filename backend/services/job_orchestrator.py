from services.workspace_service import cleanup_workspace
from services.zip_input_service import handle_zip_input
from services.repo_input_service import clone_github_repository
from services.job_admission import admit_job


class JobOrchestrator:
    """
    Central authority for job admission.
    Workspace lifecycle is delegated to workspace_service.
    """

    def create_job_from_zip_input(self, *, file, metadata: dict):
        workspace = None

        try:
            workspace = handle_zip_input(file)

            return admit_job(
                workspace=workspace,
                stack=metadata["stack"],
                versions=metadata.get("versions", {}),
                pipeline=metadata["pipeline"],
            )

        except Exception:
            if workspace:
                cleanup_workspace(workspace)
            raise

    def create_job_from_repo_input(self, *, github_url: str, metadata: dict):
        workspace = None

        try:
            workspace = clone_github_repository(github_url)

            return admit_job(
                workspace=workspace,
                stack=metadata["stack"],
                versions=metadata.get("versions", {}),
                pipeline=metadata["pipeline"],
            )

        except Exception:
            if workspace:
                cleanup_workspace(workspace)
            raise
