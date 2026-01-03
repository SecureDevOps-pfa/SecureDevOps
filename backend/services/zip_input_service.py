import io
import zipfile
import shutil
from pathlib import Path
from fastapi import UploadFile

from config import (
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
from services.workspace_service import create_workspace, cleanup_workspace


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

    workspace = create_workspace()

    try:
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

                target_path = safe_extract_path(
                    workspace.source_dir, entry.filename
                )

                reject_dangerous_file(target_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)

                with zf.open(entry) as src, open(target_path, "wb") as dst:
                    dst.write(src.read())

        _normalize_single_root_directory(workspace.source_dir)
        return workspace

    except Exception:
        cleanup_workspace(workspace)
        raise

