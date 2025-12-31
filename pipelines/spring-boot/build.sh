#!/usr/bin/env bash
set -Eeuo pipefail

STAGE="build"
REPORT_DIR="/reports/${STAGE}"
REPORT_FILE="${REPORT_DIR}/result.json"
LOG_FILE="${REPORT_DIR}/${STAGE}.log"

mkdir -p "${REPORT_DIR}"

START_TS=$(date +%s%3N)

if mvn -f /app/pom.xml -DskipTests compile > "$LOG_FILE" 2>&1; then
  STATUS="SUCCESS"
  MESSAGE="Compilation succeeded"
  EXIT_CODE=0
else
  STATUS="FAILED"
  MESSAGE="Compilation failed , see logs at ${REPORT_DIR}/${LOG_FILE} "
  EXIT_CODE=1
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

exit ${EXIT_CODE}
