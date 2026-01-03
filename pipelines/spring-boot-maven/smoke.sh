#!/usr/bin/env bash
set -Eeuo pipefail

: "${APP_DIR:?APP_DIR not set}"
: "${REPORTS_DIR:?REPORTS_DIR not set}"

STAGE="smoke-test"

REPORT_DIR="${REPORTS_DIR}/${STAGE}"
REPORT_FILE="${REPORT_DIR}/result.json"
LOG_FILE="${REPORT_DIR}/${STAGE}.log"

mkdir -p "${REPORT_DIR}"

START_TS=$(date +%s%3N)

JAR_FILE=$(ls "${APP_DIR}/target/"*.jar 2>/dev/null | head -n 1)

if [[ -z "${JAR_FILE}" ]]; then
  cat > "${REPORT_FILE}" <<EOF
{
  "stage": "${STAGE}",
  "status": "FAILED",
  "duration_ms": 0,
  "message": "No JAR found to run"
}
EOF
  exit 1
fi

echo "Starting app: ${JAR_FILE}"
java -jar "${JAR_FILE}" >"$LOG_FILE" 2>&1 &
APP_PID=$!

echo "Waiting 10s for app to initialize..."
sleep 10

READY=false
for i in $(seq 1 10); do
  echo "Health check attempt $i..."
  if curl -fs http://localhost:8080/actuator/health >/dev/null 2>&1; then
    READY=true
    break
  fi
  sleep 3
done

echo "Stopping app..."
kill "$APP_PID" >/dev/null 2>&1 || true
wait "$APP_PID" 2>/dev/null || true

END_TS=$(date +%s%3N)
DURATION=$((END_TS - START_TS))

if [[ "$READY" == true ]]; then
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
  "duration_ms": ${DURATION},
  "message": "${MESSAGE}"
}
EOF

exit ${EXIT_CODE}
