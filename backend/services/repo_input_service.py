import shutil
import subprocess
import os
import stat

from pathlib import Path
from urllib.parse import urlparse

from config import WORKSPACES_DIR, GIT_CLONE_TIMEOUT, GIT_MAX_DEPTH
from utils.repo_safety import scan_repo
from config import MAX_FILES, MAX_UNCOMPRESSED_BYTES, MAX_DEPTH

def _force_remove(path: Path):
    """
    Windows-safe recursive delete.
    Removes read-only flags before deletion.
    """

    def onerror(func, p, exc_info):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    shutil.rmtree(path, onerror=onerror)

def _is_valid_github_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "github.com"
        and len(parsed.path.strip("/").split("/")) == 2
    )


def _generate_job_id() -> str:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(p for p in WORKSPACES_DIR.glob("job-*") if p.is_dir())
    return f"job-{len(existing) + 1:03d}"


def clone_github_repository(github_url: str):
    if not _is_valid_github_url(github_url):
        raise ValueError("Only public GitHub repositories are allowed")

    job_id = _generate_job_id()
    job_dir = WORKSPACES_DIR / job_id
    source_dir = job_dir / "source"

    try:
        source_dir.mkdir(parents=True, exist_ok=False)

        subprocess.run(
            [
                "git",
                "clone",
                "--depth", str(GIT_MAX_DEPTH),
                "--no-tags",
                "--single-branch",
                github_url,
                str(source_dir),
            ],
            timeout=GIT_CLONE_TIMEOUT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        git_dir = source_dir / ".git"
        if git_dir.exists():
            _force_remove(git_dir)

        scan_repo(
            source_dir,
            max_files=MAX_FILES,
            max_bytes=MAX_UNCOMPRESSED_BYTES,
            max_depth=MAX_DEPTH,
        )

        return job_dir, source_dir

    except Exception:
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
        raise
