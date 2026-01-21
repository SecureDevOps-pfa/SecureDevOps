#!/usr/bin/env bash
set -Euo pipefail

REPORTS_DIR="${REPORTS_DIR:-../reports}"
APP_DIR="${APP_DIR:-.}"

STAGE="smoke-test"

REPORT_DIR="${REPORTS_DIR}/${STAGE}"
REPORT_FILE="${REPORT_DIR}/result.json"
LOG_FILE="${REPORT_DIR}/${STAGE}.log"
APP_PORT="${APP_PORT:-8080}"

mkdir -p "${REPORT_DIR}"

START_TS=$(date +%s%3N)

# ---- GUARANTEE RESULT.JSON EVEN ON CRASH ----
trap '{
  END_TS=$(date +%s%3N)
  DURATION=$((END_TS - START_TS))
  cat > "${REPORT_FILE}" <<EOF
{
  "stage": "${STAGE}",
  "status": "FAILED",
  "duration_ms": ${DURATION},
  "message": "Smoke-test script crashed before completion"
}
EOF
}' ERR

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
  if nc -z localhost "${APP_PORT}"; then
    READY=true
    break
  fi
  sleep 3
done


echo "Stopping app..."
kill "$APP_PID" >/dev/null 2>&1 || true
# Give JVM time to exit cleanly
for i in $(seq 1 10); do
  if ps -p "$APP_PID" > /dev/null; then
    sleep 1
  else
    break
  fi
done

# Force kill if still alive
if ps -p "$APP_PID" > /dev/null; then
  echo "Force killing app..."
  kill -9 "$APP_PID" >/dev/null 2>&1 || true
fi
wait "$APP_PID" 2>/dev/null || true

END_TS=$(date +%s%3N)
DURATION=$((END_TS - START_TS))

if [[ "$READY" == true ]]; then
  STATUS="SUCCESS"
  MESSAGE="Application started and health endpoint is reachable"
  EXIT_CODE=0
else
  STATUS="FAILURE"
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
