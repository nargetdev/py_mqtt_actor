#!/usr/bin/env bash
set -euo pipefail

# Test script to demonstrate UUID parsing functionality
# This script tests both scenarios:
# 1. Request without UUID (should generate one)
# 2. Request with UUID (should use the provided one)

command -v mosquitto_pub >/dev/null 2>&1 || {
  echo "mosquitto_pub not found. Install mosquitto-clients and retry." >&2
  exit 127
}

BROKER=${MQTT_BROKER:-localhost}
PORT=${MQTT_PORT:-1883}
RECIPIENT=${1:-ALL}
SERVICE=${2:-example-service}

echo "Testing UUID parsing functionality..."
echo "Broker: ${BROKER}:${PORT}"
echo "Recipient: ${RECIPIENT}"
echo "Service: ${SERVICE}"
echo ""

# Test 1: Request without UUID (should generate one)
echo "Test 1: Request without UUID (should generate one)"
TOPIC1="REQ/${RECIPIENT}/${SERVICE}"
PAYLOAD='{"message": "test without UUID", "delay_seconds": 1}'
echo "Publishing to: ${TOPIC1}"
echo "Payload: ${PAYLOAD}"
mosquitto_pub -h "${BROKER}" -p "${PORT}" -t "${TOPIC1}" -m "${PAYLOAD}"
echo "Published. Check logs for generated UUID."
echo ""

# Wait a bit
sleep 1

# Test 2: Request with UUID (should use the provided one)
echo "Test 2: Request with UUID (should use the provided one)"
CUSTOM_UUID="abc12345"
TOPIC2="REQ/${RECIPIENT}/${SERVICE}/${CUSTOM_UUID}"
PAYLOAD='{"message": "test with custom UUID", "delay_seconds": 1}'
echo "Publishing to: ${TOPIC2}"
echo "Payload: ${PAYLOAD}"
echo "Expected UUID in response: ${CUSTOM_UUID}"
mosquitto_pub -h "${BROKER}" -p "${PORT}" -t "${TOPIC2}" -m "${PAYLOAD}"
echo "Published. Check logs for used UUID."
echo ""

# Wait a bit
sleep 1

# Test 3: Another request with different UUID
echo "Test 3: Another request with different UUID"
CUSTOM_UUID2="def67890"
TOPIC3="REQ/${RECIPIENT}/${SERVICE}/${CUSTOM_UUID2}"
PAYLOAD='{"message": "test with another custom UUID", "delay_seconds": 1}'
echo "Publishing to: ${TOPIC3}"
echo "Payload: ${PAYLOAD}"
echo "Expected UUID in response: ${CUSTOM_UUID2}"
mosquitto_pub -h "${BROKER}" -p "${PORT}" -t "${TOPIC3}" -m "${PAYLOAD}"
echo "Published. Check logs for used UUID."
echo ""

echo "All tests completed. Check the actor logs to verify:"
echo "1. First request should show 'Generated request ID: <uuid>'"
echo "2. Second request should show 'Using provided request ID: abc12345'"
echo "3. Third request should show 'Using provided request ID: def67890'"
echo ""
echo "Response topics should be:"
echo "1. RESP/<hostname>/<service>/<generated_uuid>/RESULT/JSON"
echo "2. RESP/<hostname>/<service>/abc12345/RESULT/JSON"
echo "3. RESP/<hostname>/<service>/def67890/RESULT/JSON"
