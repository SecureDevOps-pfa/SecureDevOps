from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACES_DIR = Path("/workspaces")
HOST_WORKSPACES_PATH = os.getenv("HOST_WORKSPACES_PATH", str(WORKSPACES_DIR))

MAX_UPLOAD_BYTES = 50 * 1024 * 1024        # 50 MB
MAX_FILES = 10_000
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024 # 200 MB
MAX_DEPTH = 25

GIT_CLONE_TIMEOUT = 60          # seconds
GIT_MAX_DEPTH = 1               # shallow clone
