#!/usr/bin/env bash
set -Eeuo pipefail

REPORTS_DIR="${REPORTS_DIR:-../reports}"
APP_DIR="${APP_DIR:-../source}"
STAGE="secrets-dir"
REPORT_DIR="${REPORTS_DIR}/${STAGE}"
REPORT_FILE="${REPORT_DIR}/result.json"
LOG_FILE="${REPORT_DIR}/${STAGE}.json"

mkdir -p "${REPORT_DIR}"

# -------------------------------
# Core command (user can override)
# -------------------------------
: "${TOOL_CMD:=gitleaks dir \"$APP_DIR\" --report-format json --report-path \"$LOG_FILE\"}"

START_TS=$(date +%s%3N)

eval "$TOOL_CMD"
EXIT_CODE=$?

# -------------------------------
# Standardized exit code handling
# -------------------------------
case $EXIT_CODE in
  0) STATUS="SUCCESS"; MESSAGE="no leaks found" ;;
  1) STATUS="FAILURE"; MESSAGE="leaks found, see $LOG_FILE for details" ;;
  2) STATUS="ERROR"; MESSAGE="tool error" ;;
  *) STATUS="UNKNOWN"; MESSAGE="unknown exit code $EXIT_CODE" ;;
esac

END_TS=$(date +%s%3N)
DURATION=$((END_TS - START_TS))

cat > "${REPORT_FILE}" <<EOF
{
  "stage": "${STAGE}",
  "status": "${STATUS}",
  "duration_ms": ${DURATION},
  "message": "${MESSAGE}"
}
EOF

exit $EXIT_CODE
