#!/usr/bin/env python3
"""
Canonical usage of py_mqtt_actor with inline Pydantic models and example JSON.

This example creates a function-based actor using MQTTActorShim. It validates
incoming requests against a Pydantic model and publishes structured responses.

Request topic(s):
  - REQ/ALL/example-service
  - REQ/{hostname}/example-service

Responses:
  RESP/{hostname}/{service}/{request_id}/{stage}/{format}
  where stage ∈ {ACK, RESULT, STATUS} and format ∈ {JSON, EMOJI}
"""

import argparse
from datetime import datetime

from pydantic import BaseModel
from typing import Optional


from py_mqtt_actor import MQTTActorShim


class ExampleRequest(BaseModel):
    """Schema for incoming requests"""
    message: str
    delay_seconds: int = 0


class ExampleResponse(BaseModel):
    """Schema for outgoing responses"""
    status: str
    result: Optional[str] = None
    processed_at: Optional[str] = None


# An inline JSON string showing a valid request payload for this service.
# Publish this string to topic "REQ/ALL/example-service".
EXAMPLE_REQUEST_JSON = """
{
  "message": "Hello from py_mqtt_actor",
  "delay_seconds": 0
}
"""

# Example mosquitto_pub command to test this service:
#
# mosquitto_pub -t REQ/soma.local/example-service -m '{
#     "message": "JELLO py_mqtt_actor",
#     "delay_seconds": 45
#   }'
#
# Or publish to the broadcast topic:
# mosquitto_pub -t REQ/ALL/example-service -m '{
#     "message": "Hello from py_mqtt_actor",
#     "delay_seconds": 0
#   }'



def process_example(request_data: ExampleRequest, request_id: str, actor_instance=None) -> ExampleResponse:
    """Business logic for handling a request.

    - request_data: validated ExampleRequest instance
    - request_id: unique identifier for this request
    - actor_instance: optional MQTTActorShim (not used here)
    """
    # Simulate some processing and return a response
    return ExampleResponse(
        status="success",
        result=f"Processed: {request_data.message}",
        processed_at=datetime.now().isoformat(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical py_mqtt_actor example-service")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    args = parser.parse_args()

    try:
        actor = MQTTActorShim(
            service_name="example-service",
            mqtt_broker=args.mqtt_broker,
            mqtt_port=args.mqtt_port,
            request_schema=ExampleRequest,
            response_schema=ExampleResponse,
            log_level=args.log_level,
            process_function=process_example,
        )
        actor.start()
    except Exception as e:
        print(f"Failed to start actor: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
