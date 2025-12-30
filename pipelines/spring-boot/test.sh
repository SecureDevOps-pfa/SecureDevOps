#!/usr/bin/env bash
set -Eeuo pipefail

STAGE="test"
REPORT_DIR="/reports/${STAGE}"
REPORT_FILE="${REPORT_DIR}/result.json"

mkdir -p "${REPORT_DIR}"

START_TS=$(date +%s%3N)

if mvn -f /app/pom.xml test >/dev/null 2>&1; then
  STATUS="SUCCESS"
  MESSAGE="All tests passed"
  EXIT_CODE=0
else
  STATUS="FAILED"
  MESSAGE="Test failures detected"
  EXIT_CODE=1
fi

END_TS=$(date +%s%3N)
DURATION=$((END_TS - START_TS))

cat > "${REPORT_FILE}" <<EOF
{
  "stage": "${STAGE}",
  "status": "${STATUS}",
  "timestamp": "$(date -Iseconds)",
  "duration_ms": ${DURATION},
  "details": {
    "message": "${MESSAGE}"
  }
}
EOF

exit ${EXIT_CODE}
