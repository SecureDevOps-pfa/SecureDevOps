import subprocess
import shutil
import os
import stat
from pathlib import Path
from urllib.parse import urlparse

from config import (
    GIT_CLONE_TIMEOUT,
    GIT_MAX_DEPTH,
    MAX_FILES,
    MAX_UNCOMPRESSED_BYTES,
    MAX_DEPTH,
)
from utils.repo_safety import scan_repo
from services.workspace_service import create_workspace, cleanup_workspace


def _force_remove(path: Path):
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


def clone_github_repository(github_url: str):
    if not _is_valid_github_url(github_url):
        raise ValueError("Only public GitHub repositories are allowed")

    workspace = create_workspace()

    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                str(GIT_MAX_DEPTH),
                "--no-tags",
                "--single-branch",
                github_url,
                str(workspace.source_dir),
            ],
            timeout=GIT_CLONE_TIMEOUT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        git_dir = workspace.source_dir / ".git"
        if git_dir.exists():
            _force_remove(git_dir)

        scan_repo(
            workspace.source_dir,
            max_files=MAX_FILES,
            max_bytes=MAX_UNCOMPRESSED_BYTES,
            max_depth=MAX_DEPTH,
        )

        return workspace

    except Exception:
        cleanup_workspace(workspace)
        raise
