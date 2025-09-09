#!/usr/bin/env python3
"""
Function-based MQTT Actor Example

Demonstrates how to create an MQTT actor by passing a function to the constructor
instead of subclassing and implementing process_request.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from py_mqtt_actor import MQTTActorShim
from INTERFACE import TestObject, ResponseObject


def process_test_object(request_data: TestObject, request_id: str, actor_instance=None) -> ResponseObject:
    """
    Process a TestObject request by writing it to a JSON file.
    
    Args:
        request_data: Validated TestObject instance
        request_id: Unique identifier for this request
        actor_instance: Optional MQTTActorShim instance for SYNC publishing
        
    Returns:
        ResponseObject: Response data to be sent back to the client
    """
    # The shim will pass a TestObject instance when annotated accordingly
    model = request_data
    
    # Build a timestamped, request-specific filename
    output_dir = Path("./prints")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"test-object-{ts}-{request_id}.json"
    
    # Serialize and write to disk
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(model.model_dump(), f, indent=2)
    
    # Publish SYNC notice for external consumers
    if actor_instance:
        actor_instance.publish_sync_notice(output_path)
    
    # Return ResponseObject instance
    return ResponseObject(
        status=200,
        output_file=str(output_path)
    )


def main() -> int:
    """Main function demonstrating function-based actor creation"""
    parser = argparse.ArgumentParser(description="Function-based TestObject Printer MQTT Actor")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    args = parser.parse_args()

    try:
        # Create actor by passing the function to the constructor
        actor = MQTTActorShim(
            service_name="test-object-printer",
            mqtt_broker=args.mqtt_broker,
            mqtt_port=args.mqtt_port,
            request_schema=TestObject,
            response_schema=None,
            log_level=args.log_level,
            process_function=process_test_object  # <-- This is the key part!
        )
        actor.start()
    except Exception as e:
        print(f"Failed to start actor: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
