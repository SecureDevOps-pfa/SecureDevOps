#!/usr/bin/env bash
set -Eeuo pipefail

STAGE="dast"
REPORTS_DIR="${REPORTS_DIR:-../reports}"
DOCKER_NETWORK="${DOCKER_NETWORK:-pipelinex-network}"
REPORT_DIR="${REPORTS_DIR}/${STAGE}"
REPORT_FILE="${REPORT_DIR}/result.json"


APP_PORT="${APP_PORT:-8080}"
TARGET_URL="http://app:${APP_PORT}"

mkdir -p "${REPORT_DIR}"

START_TS=$(date +%s%3N)

#raw command, ill keep it for now . 
# docker run --rm \
#   --network "${DOCKER_NETWORK}" \
#   -v "${REPORT_DIR}:/zap/wrk" \
#   ghcr.io/zaproxy/zaproxy:stable \
#   zap-baseline.py \
#     -t "${TARGET_URL}" \
#     -J dast.json \
#     -r dast.html

# assumes to be ran from docker-compose.dast.yml
zap-baseline.py \
  -t "${TARGET_URL}" \
  -J dast.json \
  -r dast.html

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    STATUS="SUCCESS"
    MESSAGE="No security issues found"
elif [ $EXIT_CODE -eq 1 ]; then
    STATUS="WARN"
    MESSAGE="Security findings detected"
elif [ $EXIT_CODE -eq 2 ]; then
    STATUS="ERROR"
    MESSAGE="ZAP execution error"
else
    STATUS="UNKNOWN"
    MESSAGE="Unknown exit code $EXIT_CODE"
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

# Do NOT fail pipeline on findings by default
if [ "$EXIT_CODE" -eq 2 ]; then
  exit 2
else
  exit 0
fi
