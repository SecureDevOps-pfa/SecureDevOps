#!/usr/bin/env bash
set -Eeuo pipefail

STAGE="${STAGE}"
REPORTS_DIR="${REPORTS_DIR:-../reports}"
APP_DIR="${APP_DIR:-../source}"
REPORT_DIR="${REPORTS_DIR}/${STAGE}"
REPORT_FILE="${REPORT_DIR}/result.json"
LOG_FILE="${REPORT_DIR}/${STAGE}${LOG_EXT:-.json}"

: "${INSTALL_CMD:?INSTALL_CMD must be set}"
: "${TOOL_CMD:?TOOL_CMD must be set}"

mkdir -p "${REPORT_DIR}"

write_report() {
  local status="$1" message="$2" duration_ms="$3"
  cat > "${REPORT_FILE}" <<EOF
{
  "stage": "${STAGE}",
  "status": "${status}",
  "duration_ms": ${duration_ms},
  "message": "${message}"
}
EOF
}

START_TS=$(date +%s%3N)
EXIT_CODE=0

# ----- Block sudo -----
if [[ "$INSTALL_CMD" == *sudo* ]]; then
  END_TS=$(date +%s%3N)
  DURATION=$((END_TS - START_TS))
  write_report "FAILED" "sudo is not allowed in commands" "$DURATION"
  exit 1
fi

# ----- Install tool -----
bash -c "$INSTALL_CMD" || EXIT_CODE=$?

# ----- Run tool -----
bash -c "$TOOL_CMD" || EXIT_CODE=$?

# ----- Standardized exit code -----
case $EXIT_CODE in
  0) STATUS="SUCCESS"; MESSAGE="no leaks found" ;;
  1) STATUS="SUCCESS"; MESSAGE="leaks found, see $LOG_FILE for details" ;;
  2) STATUS="FAILED"; MESSAGE="tool error" ;;
  *) STATUS="UNKNOWN"; MESSAGE="unknown exit code $EXIT_CODE" ;;
esac

END_TS=$(date +%s%3N)
DURATION=$((END_TS - START_TS))
write_report "$STATUS" "$MESSAGE" "$DURATION"

exit $EXIT_CODE

