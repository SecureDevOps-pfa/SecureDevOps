## scripts 
Strict shell mode (set -Eeuo pipefail)

- -e : Exit immediately if a command fails (non-zero exit code), except when the command is part of an if / while / until / && / || construct.
- -u : Treat the use of unset variables as an error and exit immediately (prevents silent misconfiguration).
- -o pipefail : In a pipeline, the exit code is the first failing command, not the last one (avoids masking errors in pipes).
- -E : Ensures that ERR traps are inherited by functions and subshells (only relevant if trap ERR is defined).

This mode enforces fail-fast behavior and prevents silent or partially successful executions.

- for custum scripts mention to user that the runner env is x86_64 Linux (when they wanty to install )
- the user command should expect to write to one output named `"${LOG_FILE}"` and the directory of the project to be `"$APP_DIR"`



update docker way to use always pull like in here : 
docker run --pull=always --rm -it \
  -u 10001:10001 \
  -v /home/abderrahmane/Desktop/SecureDevOps/test/source:/home/runner/source:rw \
  -v /home/abderrahmane/Desktop/SecureDevOps/test/pipelines:/home/runner/pipelines:ro \
  -v /home/abderrahmane/Desktop/SecureDevOps/test/reports:/home/runner/reports:rw \
  -w /home/runner \
  abderrahmane03/pipelinex:java17-mvn3.9.12-latest