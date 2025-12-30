from pathlib import Path

BLOCKED_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib",
    ".bin", ".class", ".jar",
    ".msi", ".app",
    ".deb", ".rpm",
    ".iso", ".img"
}

def reject_dangerous_file(path: Path):
    if path.suffix.lower() in BLOCKED_EXTENSIONS:
        raise ValueError(f"Dangerous file type detected: {path.name}")
