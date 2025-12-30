#!/usr/bin/env bash
set -Eeuo pipefail

STAGE="smoke"
REPORT_DIR="/reports/${STAGE}"
REPORT_FILE="${REPORT_DIR}/result.json"

mkdir -p "${REPORT_DIR}"

START_TS=$(date +%s%3N)

JAR_FILE=$(ls /app/target/*.jar | head -n 1)

if [[ -z "${JAR_FILE}" ]]; then
  cat > "${REPORT_FILE}" <<EOF
{
  "stage": "${STAGE}",
  "status": "FAILED",
  "timestamp": "$(date -Iseconds)",
  "duration_ms": 0,
  "details": {
    "message": "No JAR found to run"
  }
}
EOF
  exit 1
fi

# Start app in background
java -jar "${JAR_FILE}" >/dev/null 2>&1 &
APP_PID=$!

# Wait for app to boot (max 20s)
READY=false
for i in {1..20}; do
  if curl -fs http://localhost:8080/actuator/health >/dev/null 2>&1; then
    READY=true
    break
  fi
  sleep 1
done

# Stop app
kill "${APP_PID}" >/dev/null 2>&1 || true
wait "${APP_PID}" 2>/dev/null || true

END_TS=$(date +%s%3N)
DURATION=$((END_TS - START_TS))

if [[ "${READY}" == "true" ]]; then
  STATUS="SUCCESS"
  MESSAGE="Application started and health endpoint is reachable"
  EXIT_CODE=0
else
  STATUS="FAILED"
  MESSAGE="Health endpoint not reachable"
  EXIT_CODE=1
fi

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
