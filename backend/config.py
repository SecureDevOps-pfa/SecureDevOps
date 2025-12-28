from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
JOBS_DIR = BASE_DIR / "jobs"

MAX_UPLOAD_BYTES = 50 * 1024 * 1024        # 50 MB
MAX_FILES = 10_000
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024 # 200 MB
MAX_DEPTH = 5
