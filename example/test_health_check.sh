#!/usr/bin/env bash
set -euo pipefail

# Test script to verify EMQX health check is working
# This script can be used to manually test the MQTT broker health

BROKER=${MQTT_BROKER:-localhost}
PORT=${MQTT_PORT:-1883}

echo "Testing MQTT broker health at ${BROKER}:${PORT}..."

# Test basic connectivity
if mosquitto_pub -h "${BROKER}" -p "${PORT}" -t "$$SYS/health" -m "health_check" -q 1; then
  echo "✅ MQTT broker is healthy and responding"
  exit 0
else
  echo "❌ MQTT broker is not responding"
  exit 1
fi
