#!/usr/bin/env python3
"""
MQTT Actor Factory

Provides factory functions for creating MQTT actors with different processing functions.
"""

from typing import Callable, Optional, Type
from pathlib import Path
import json
from datetime import datetime

from py_mqtt_actor import MQTTActorShim
from pydantic_interface import TestObject


def create_test_object_printer(
    mqtt_broker: str,
    mqtt_port: int = 1883,
    output_dir: str = "./prints",
    log_level: str = "INFO"
) -> MQTTActorShim:
    """
    Create a TestObject printer actor using a function-based approach.
    
    Args:
        mqtt_broker: MQTT broker address
        mqtt_port: MQTT broker port
        output_dir: Directory to write JSON files
        log_level: Logging level
        
    Returns:
        MQTTActorShim: Configured actor instance
    """
    def process_test_object(request_data: dict, request_id: str, actor_instance=None) -> dict:
        """Process TestObject by writing to JSON file"""
        model = TestObject(**request_data)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        file_path = output_path / f"test-object-{ts}-{request_id}.json"
        
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(model.model_dump(), f, indent=2)
        
        # Publish SYNC notice for external consumers
        if actor_instance:
            actor_instance.publish_sync_notice(file_path)
        
        return {
            "written": True,
            "output_file": str(file_path),
            "string_element": model.string_element,
            "priority": model.priority,
            "simple_object": model.simple_object.model_dump(),
        }
    
    return MQTTActorShim(
        service_name="test-object-printer",
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        request_schema=TestObject,
        response_schema=None,
        log_level=log_level,
        process_function=process_test_object
    )


def create_generic_actor(
    service_name: str,
    process_function: Callable[[dict, str], dict],
    mqtt_broker: str,
    mqtt_port: int = 1883,
    request_schema: Optional[Type] = None,
    response_schema: Optional[Type] = None,
    log_level: str = "INFO"
) -> MQTTActorShim:
    """
    Create a generic MQTT actor with a custom processing function.
    
    Args:
        service_name: Name of the service
        process_function: Function to process requests
        mqtt_broker: MQTT broker address
        mqtt_port: MQTT broker port
        request_schema: Pydantic model for request validation
        response_schema: Pydantic model for response validation
        log_level: Logging level
        
    Returns:
        MQTTActorShim: Configured actor instance
    """
    return MQTTActorShim(
        service_name=service_name,
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        request_schema=request_schema,
        response_schema=response_schema,
        log_level=log_level,
        process_function=process_function
    )


# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Factory-based MQTT Actor")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--output-dir", default="./prints", help="Directory to write JSON files")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Create actor using factory function
    actor = create_test_object_printer(
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        output_dir=args.output_dir,
        log_level=args.log_level
    )
    
    try:
        actor.start()
    except Exception as e:
        print(f"Failed to start actor: {e}")
        exit(1)
