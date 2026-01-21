## scripts 
Strict shell mode (set -Eeuo pipefail)

- -e : Exit immediately if a command fails (non-zero exit code), except when the command is part of an if / while / until / && / || construct.
- -u : Treat the use of unset variables as an error and exit immediately (prevents silent misconfiguration).
- -o pipefail : In a pipeline, the exit code is the first failing command, not the last one (avoids masking errors in pipes).
- -E : Ensures that ERR traps are inherited by functions and subshells (only relevant if trap ERR is defined).

This mode enforces fail-fast behavior and prevents silent or partially successful executions.

- for custum scripts mention to user that the runner env is x86_64 Linux (when they wanty to install )
- the user command should expect to write to one output named `"${LOG_FILE}"` and the directory of the project to be `"$APP_DIR"`