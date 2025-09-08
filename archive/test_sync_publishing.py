#!/usr/bin/env python3
"""
Test script to verify SYNC publishing works in function-based actors
"""

import json
from datetime import datetime
from pathlib import Path

from py_mqtt_actor import MQTTActorShim
from pydantic_interface import TestObject


def test_process_function(request_data: dict, request_id: str, actor_instance=None) -> dict:
    """Test function that should publish SYNC notice"""
    model = TestObject(**request_data)
    
    output_dir = Path("./test_prints")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"test-object-{ts}-{request_id}.json"
    
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(model.model_dump(), f, indent=2)
    
    # This should now publish SYNC notice
    if actor_instance:
        print(f"Publishing SYNC notice for: {output_path}")
        actor_instance.publish_sync_notice(output_path)
    else:
        print("WARNING: No actor instance provided - SYNC notice not published")
    
    return {
        "written": True,
        "output_file": str(output_path),
        "test": "sync_publishing_test"
    }


def main():
    """Test the function-based actor with SYNC publishing"""
    print("Testing function-based actor with SYNC publishing...")
    
    # Create actor with test function
    actor = MQTTActorShim(
        service_name="test-sync-publisher",
        mqtt_broker="localhost",  # Won't actually connect in this test
        mqtt_port=1883,
        request_schema=TestObject,
        process_function=test_process_function
    )
    
    # Test data
    test_data = {
        "string_element": "test_sync",
        "priority": 1.0,
        "simple_object": {
            "int_value": 42,
            "bool_value": True
        }
    }
    
    # Test the process_request method directly
    print("Testing process_request method...")
    try:
        result = actor.process_request(test_data, "test-123")
        print(f"Result: {result}")
        print("✅ Function-based actor with SYNC publishing works!")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
