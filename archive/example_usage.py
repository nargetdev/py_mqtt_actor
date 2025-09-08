#!/usr/bin/env python3
"""
Example Usage: Function-based vs Subclass-based MQTT Actors

This demonstrates both approaches for creating MQTT actors:
1. Function-based: Pass a function to the constructor
2. Subclass-based: Inherit from MQTTActorShim and implement process_request
"""

import json
from datetime import datetime
from pathlib import Path

from py_mqtt_actor import MQTTActorShim
from pydantic_interface import TestObject


# ============================================================================
# APPROACH 1: FUNCTION-BASED ACTOR
# ============================================================================

def process_test_object_function(request_data: dict, request_id: str, actor_instance=None) -> dict:
    """Function to process TestObject requests"""
    model = TestObject(**request_data)
    
    output_dir = Path("./prints")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"test-object-{ts}-{request_id}.json"
    
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(model.model_dump(), f, indent=2)
    
    # Publish SYNC notice for external consumers
    if actor_instance:
        actor_instance.publish_sync_notice(output_path)
    
    return {
        "written": True,
        "output_file": str(output_path),
        "string_element": model.string_element,
        "priority": model.priority,
        "simple_object": model.simple_object.model_dump(),
    }


def create_function_based_actor(mqtt_broker: str, mqtt_port: int = 1883) -> MQTTActorShim:
    """Create an actor using the function-based approach"""
    return MQTTActorShim(
        service_name="test-object-printer",
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        request_schema=TestObject,
        response_schema=None,
        process_function=process_test_object_function  # <-- Key difference!
    )


# ============================================================================
# APPROACH 2: SUBCLASS-BASED ACTOR (existing approach)
# ============================================================================

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
        model = TestObject(**request_data)
        
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = self.output_dir / f"test-object-{ts}-{request_id}.json"
        
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(model.model_dump(), f, indent=2)
        
        return {
            "written": True,
            "output_file": str(output_path),
            "string_element": model.string_element,
            "priority": model.priority,
            "simple_object": model.simple_object.model_dump(),
        }


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_function_based():
    """Example of using function-based approach"""
    print("Creating function-based actor...")
    actor = create_function_based_actor("localhost", 1883)
    # actor.start()  # Uncomment to actually start
    print("Function-based actor created successfully!")


def example_subclass_based():
    """Example of using subclass-based approach"""
    print("Creating subclass-based actor...")
    actor = TestObjectPrinterActor("localhost", 1883, "./prints")
    # actor.start()  # Uncomment to actually start
    print("Subclass-based actor created successfully!")


def example_generic_factory():
    """Example of using a generic factory function"""
    def my_custom_processor(request_data: dict, request_id: str) -> dict:
        """Custom processing function"""
        return {
            "processed_by": "custom_function",
            "request_id": request_id,
            "data_keys": list(request_data.keys()),
            "timestamp": datetime.now().isoformat()
        }
    
    print("Creating actor with custom processor...")
    actor = MQTTActorShim(
        service_name="custom-processor",
        mqtt_broker="localhost",
        mqtt_port=1883,
        request_schema=TestObject,
        process_function=my_custom_processor
    )
    print("Custom processor actor created successfully!")


if __name__ == "__main__":
    print("MQTT Actor Examples")
    print("==================")
    
    example_function_based()
    print()
    
    example_subclass_based()
    print()
    
    example_generic_factory()
    print()
    
    print("All examples completed!")
