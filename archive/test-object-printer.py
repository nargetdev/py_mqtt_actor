#!/usr/bin/env python3
"""
TestObject Printer Actor

Listens for MQTT requests carrying a payload matching the TestObject schema
and writes the received object to a JSON file.

Topics:
- Subscribes: REQ/ALL/test-object-printer, REQ/<hostname>/test-object-printer
- Publishes: RESP/<hostname>/test-object-printer/<request_id>/<stage>/{JSON,EMOJI}

Run:
    python3 test-object-printer.py --mqtt-broker localhost --output-dir ./prints
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from py_mqtt_actor import MQTTActorShim
from pydantic_interface import TestObject


class TestObjectPrinterActor(MQTTActorShim):
    """Actor that validates a TestObject and writes it to a JSON file."""

    def __init__(
        self,
        mqtt_broker: str,
        mqtt_port: int = 1883,
        output_dir: str = "./prints",
        log_level: str = "INFO",
    ):
        super().__init__(
            service_name="test-object-printer",
            mqtt_broker=mqtt_broker,
            mqtt_port=mqtt_port,
            request_schema=TestObject,
            response_schema=None,
            log_level=log_level,
        )
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_request(self, request_data: dict, request_id: str) -> dict:
        """Write the validated TestObject to a JSON file and return metadata."""
        # Create a Pydantic model instance (already validated by the shim)
        model = TestObject(**request_data)

        # Build a timestamped, request-specific filename
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = self.output_dir / f"test-object-{ts}-{request_id}.json"

        # Serialize and write to disk
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(model.model_dump(), f, indent=2)

        # Optionally publish a SYNC notice for external consumers
        self.publish_sync_notice(output_path)

        # Return information that will be merged into the RESULT payload
        return {
            "written": True,
            "output_file": str(output_path),
            "string_element": model.string_element,
            "priority": model.priority,
            "simple_object": model.simple_object.model_dump(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="TestObject Printer MQTT Actor")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--output-dir", default="./prints", help="Directory to write JSON files")
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    args = parser.parse_args()

    try:
        actor = TestObjectPrinterActor(
            mqtt_broker=args.mqtt_broker,
            mqtt_port=args.mqtt_port,
            output_dir=args.output_dir,
            log_level=args.log_level,
        )
        actor.start()
    except Exception as e:
        print(f"Failed to start actor: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())


