## scripts 
Strict shell mode (set -Eeuo pipefail)

-e : Exit immediately if a command fails (non-zero exit code), except when the command is part of an if / while / until / && / || construct.

-u : Treat the use of unset variables as an error and exit immediately (prevents silent misconfiguration).

-o pipefail : In a pipeline, the exit code is the first failing command, not the last one (avoids masking errors in pipes).

-E : Ensures that ERR traps are inherited by functions and subshells (only relevant if trap ERR is defined).

This mode enforces fail-fast behavior and prevents silent or partially successful executions.

