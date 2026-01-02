import io
import zipfile
import shutil
from pathlib import Path
from fastapi import UploadFile

from config import (
    WORKSPACES_DIR,
    MAX_UPLOAD_BYTES,
    MAX_FILES,
    MAX_UNCOMPRESSED_BYTES,
    MAX_DEPTH,
)
from utils.zip_safety import (
    is_valid_zip_signature,
    safe_extract_path,
    path_depth,
    reject_symlink,
)
from utils.content_safety import reject_dangerous_file


def _generate_job_id() -> str:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(p for p in WORKSPACES_DIR.glob("job-*") if p.is_dir())
    return f"job-{len(existing) + 1:03d}"

def _normalize_single_root_directory(source_dir: Path):
    entries = list(source_dir.iterdir())

    if len(entries) == 1 and entries[0].is_dir():
        root = entries[0]

        for item in root.iterdir():
            shutil.move(str(item), source_dir)

        root.rmdir()


def handle_zip_input(file: UploadFile):
    raw = file.file.read()

    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded file exceeds maximum allowed size")

    if not is_valid_zip_signature(raw[:8]):
        raise ValueError("File is not a valid ZIP archive")

    job_id = _generate_job_id()
    job_dir = WORKSPACES_DIR / job_id
    source_dir = job_dir / "source"

    try:
        source_dir.mkdir(parents=True, exist_ok=False)

        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            entries = zf.infolist()

            if len(entries) > MAX_FILES:
                raise ValueError("Too many files in ZIP archive")

            total_size = 0

            for entry in entries:
                if entry.filename.endswith("/"):
                    continue

                if path_depth(entry.filename) > MAX_DEPTH:
                    raise ValueError("ZIP directory depth exceeded")

                reject_symlink(entry)

                total_size += entry.file_size
                if total_size > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError("ZIP extraction size limit exceeded")

                target_path = safe_extract_path(source_dir, entry.filename)
                reject_dangerous_file(target_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)

                with zf.open(entry) as src, open(target_path, "wb") as dst:
                    dst.write(src.read())
                    
            _normalize_single_root_directory(source_dir)
        return job_dir, source_dir

    except Exception:
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
        raise
