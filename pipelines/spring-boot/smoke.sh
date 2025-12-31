#!/usr/bin/env bash
set -Eeuo pipefail

STAGE="smoke test"
REPORT_DIR="/reports/${STAGE}"
REPORT_FILE="${REPORT_DIR}/result.json"
LOG_FILE="${REPORT_DIR}/${STAGE}.log"

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
java -jar "${JAR_FILE}" >"$LOG_FILE" 2>&1 &
APP_PID=$!

# Wait for app to boot (max 30s)
READY=false
for i in {1..30}; do
  if curl -fs http://localhost:8080/actuator/health >"$LOG_FILE" 2>&1; then
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
  MESSAGE="${STAGE} stage failed , see logs at ${LOG_FILE} "
  EXIT_CODE=1
fi

cat > "${REPORT_FILE}" <<EOF
{
  "stage": "${STAGE}",
  "status": "${STATUS}",
  "duration_ms": ${DURATION},
  "message": "${MESSAGE}"
}
EOF

exit ${EXIT_CODE}
