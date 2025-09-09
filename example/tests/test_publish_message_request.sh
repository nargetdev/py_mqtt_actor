#!/usr/bin/env bash
set -euo pipefail

# Simple helper to continuously publish a TestObject request to the test-object-printer actor every 2s
# Defaults:
#   broker: localhost
#   recipient: ALL
#   service: test-object-printer
#   port: 1883
#   payload: built-in valid TestObject JSON (can be overridden by file arg)
#
# Usage:
#   ./test_publish_message_request.sh [broker] [recipient] [service] [port] [payload_file]
#
# Examples:
#   ./test_publish_message_request.sh
#   ./test_publish_message_request.sh 192.168.1.100 ALL
#   ./test_publish_message_request.sh localhost $(hostname) test-object-printer 1883 ./payload.json

command -v mosquitto_pub >/dev/null 2>&1 || {
  echo "mosquitto_pub not found. Install mosquitto-clients and retry." >&2
  exit 127
}

BROKER=${MQTT_BROKER:-localhost}
PORT=${MQTT_PORT:-1883}
RECIPIENT=${2:-ALL}
SERVICE=${3:-test-object-printer}
PAYLOAD_FILE=${5:-}

TOPIC="REQ/${RECIPIENT}/${SERVICE}"

# Retry logic: try up to 5 times with 2s delay between attempts
MAX_ATTEMPTS=5
SLEEP_BETWEEN=2


echo "Starting to publish messages to topic '${TOPIC}' every 2 seconds. Press Ctrl+C to stop."

while true; do
    # Default valid TestObject payload
  PAYLOAD='{
    "string_element": "hello-from-cli",
    "priority": 0.9,
    "simple_object": {
      "int_value": 42,
      "bool_value": true
    }
  }'
  echo "mosquitto_pub -h \"${BROKER}\" -p \"${PORT}\" -t \"${TOPIC}\" -m '${PAYLOAD}'"
  mosquitto_pub -h "${BROKER}" -p "${PORT}" -t "${TOPIC}" -m "${PAYLOAD}"
  echo "Published. Waiting 2s before next publish..."
  sleep 2
done
