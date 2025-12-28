import os
from pathlib import Path
import zipfile

def is_valid_zip_signature(data: bytes) -> bool:
    return (
        data.startswith(b"PK\x03\x04")
        or data.startswith(b"PK\x05\x06")
        or data.startswith(b"PK\x07\x08")
    )

def safe_extract_path(base: Path, member_name: str) -> Path:
    target = (base / member_name).resolve()
    base = base.resolve()

    if not str(target).startswith(str(base) + os.sep) and target != base:
        raise ValueError(f"Path traversal detected: {member_name}")

    return target

def path_depth(path: str) -> int:
    return len([p for p in path.replace("\\", "/").split("/") if p])

def reject_symlink(zip_info: zipfile.ZipInfo):
    # Detect Unix symlink
    is_symlink = (zip_info.external_attr >> 16) & 0o170000 == 0o120000
    if is_symlink:
        raise ValueError(f"Symlink detected in zip: {zip_info.filename}")
