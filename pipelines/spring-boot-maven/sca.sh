#!/usr/bin/env bash
set -Eeuo pipefail

REPORTS_DIR="${REPORTS_DIR:-../reports}"
APP_DIR="${APP_DIR:-../source}"

STAGE="sca"
REPORT_DIR="${REPORTS_DIR}/${STAGE}"
REPORT_FILE="${REPORT_DIR}/result.json"
LOG_FILE="${REPORT_DIR}/${STAGE}.json"

mkdir -p "${REPORT_DIR}"

START_TS=$(date +%s%3N)

#l || to prevent set -e and -u from killing the pipeline
EXIT_CODE=0
trivy fs --scanners vuln "${APP_DIR}/pom.xml" --format json --output "${LOG_FILE}" || EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    STATUS="SUCCESS"
    MESSAGE="No issues found in ${APP_DIR}"
elif [ $EXIT_CODE -eq 1 ]; then
    STATUS="SUCCESS"
    MESSAGE="Issues found in ${APP_DIR}, see ${LOG_FILE} for details"
elif [ $EXIT_CODE -eq 2 ]; then
    STATUS="FAILURE"
    MESSAGE="Semgrep execution error"
else
    STATUS="FAILURE"
    MESSAGE="Unknown exit code $EXIT_CODE "
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