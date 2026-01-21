#!/usr/bin/env bash
set -Eeuo pipefail

REPORTS_DIR="${REPORTS_DIR:-../reports}"
APP_DIR="${APP_DIR:-../source}"

STAGE="secrets-git"
REPORT_DIR="${REPORTS_DIR}/${STAGE}"
REPORT_FILE="${REPORT_DIR}/result.json"
LOG_FILE="${REPORT_DIR}/${STAGE}.json"

mkdir -p "${REPORT_DIR}"

START_TS=$(date +%s%3N)

EXIT_CODE=0
gitleaks git "$APP_DIR" --report-format json --report-path "${LOG_FILE}" || EXIT_CODE=$?


if [ $EXIT_CODE -eq 0 ]; then
    STATUS="SUCCESS"
    MESSAGE="no leaks found"
elif [ $EXIT_CODE -eq 1 ]; then
    STATUS="SUCCESS"
    MESSAGE="leaks found, see $LOG_FILE for details"
elif [ $EXIT_CODE -eq 2 ]; then
    STATUS="FAILURE"
    MESSAGE="tool error"
else
    STATUS="FAILURE"
    MESSAGE="unknown exit code $EXIT_CODE"
fi

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