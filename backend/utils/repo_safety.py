from pathlib import Path
from utils.content_safety import reject_dangerous_file
from utils.zip_safety import path_depth

def scan_repo(
    repo_dir: Path,
    *,
    max_files: int,
    max_bytes: int,
    max_depth: int,
):
    total_size = 0
    file_count = 0

    for path in repo_dir.rglob("*"):
        if path.is_dir():
            continue

        file_count += 1
        if file_count > max_files:
            raise ValueError("Repository contains too many files")

        if path_depth(str(path.relative_to(repo_dir))) > max_depth:
            raise ValueError("Repository directory depth exceeded")

        size = path.stat().st_size
        total_size += size
        if total_size > max_bytes:
            raise ValueError("Repository size limit exceeded")

        reject_dangerous_file(path)
