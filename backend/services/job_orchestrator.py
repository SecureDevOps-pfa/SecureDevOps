import shutil
from pathlib import Path

from services.zip_input_service import handle_zip_input
from services.repo_input_service import clone_github_repository
from services.job_admission import admit_job


class JobOrchestrator:
    """
    Central authority for job creation & lifecycle.
    """

    def create_job_from_zip_input(self, *, file, metadata: dict):
        job_dir = None

        try:
            job_dir, source_dir = handle_zip_input(file)

            return admit_job(
                job_dir=job_dir,
                source_dir=source_dir,
                stack=metadata["stack"],
                versions=metadata.get("versions", {}),
                pipeline=metadata["pipeline"],
            )

        except Exception:
            self._cleanup(job_dir)
            raise

    def create_job_from_repo_input(self, *, github_url: str, metadata: dict):
        job_dir = None

        try:
            job_dir, source_dir = clone_github_repository(github_url)

            return admit_job(
                job_dir=job_dir,
                source_dir=source_dir,
                stack=metadata["stack"],
                versions=metadata.get("versions", {}),
                pipeline=metadata["pipeline"],
            )

        except Exception:
            self._cleanup(job_dir)
            raise

    def _cleanup(self, job_dir: Path | None):
        if job_dir and job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
