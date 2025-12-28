import io
import json
import time
import zipfile
from pathlib import Path

from config import (
    JOBS_DIR,
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

def generate_job_id() -> str:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted([p for p in JOBS_DIR.glob("job-*") if p.is_dir()])
    return f"job-{len(existing) + 1:03d}"


def handle_zip_upload(file_storage):
    """
    Securely processes an uploaded ZIP file by validating size and format,
    creating an isolated job directory, and safely extracting contents.

    Enforces limits on file count, directory depth, total uncompressed size,
    and rejects symlinks and path traversal to prevent ZIP bomb and filesystem
    escape attacks. Writes job metadata on success and fails fast on any
    validation error.
    """
    raw = file_storage.read()

    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded file exceeds maximum allowed size")

    if not is_valid_zip_signature(raw[:8]):
        raise ValueError("File is not a valid ZIP archive")

    job_id = generate_job_id()
    job_dir = JOBS_DIR / job_id
    source_dir = job_dir / "source"

    source_dir.mkdir(parents=True, exist_ok=False)
    (job_dir / "upload.zip").write_bytes(raw)

    total_size = 0
    file_count = 0

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        entries = zf.infolist()

        if len(entries) > MAX_FILES:
            raise ValueError("Too many files in ZIP archive")

        for entry in entries:
            if entry.filename.endswith("/"):
                continue

            if path_depth(entry.filename) > MAX_DEPTH:
                raise ValueError("ZIP directory depth exceeded")

            reject_symlink(entry)

            total_size += entry.file_size
            if total_size > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("ZIP extraction size limit exceeded")

            file_count += 1

            target_path = safe_extract_path(source_dir, entry.filename)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            with zf.open(entry) as src, open(target_path, "wb") as dst:
                dst.write(src.read())

    metadata = {
        "job_id": job_id,
        "status": "UPLOADED",
        "current_stage": "input_handling",
        "input": {
            "type": "zip",
            "original_filename": file_storage.filename,
            "uploaded_bytes": len(raw),
            "extracted_files": file_count,
            "extracted_bytes": total_size,
        },
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    (job_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    return metadata
