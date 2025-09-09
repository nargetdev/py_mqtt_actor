---
title: py mqtt actor
description: Component specification and documentation
---


## Overview
The `py_mqtt_actor` module provides a base class for creating MQTT-based actors that follow a standard request-response pattern. Actors subscribe to request topics, process requests in background threads, and publish both EMOJI and JSON responses.

## 1. Processing Interfaces

### `process_request` Interface (Subclass Method)
```python
def process_request(self, request_data: dict, request_id: str) -> dict:
    """Process a request - must be implemented by subclasses"""
    # Business logic here
    return {"status": "success", "result": "..."}
```

### `process_function` Interface (Function-based)
```python
def process_function(request_data: Union[dict, BaseModel], request_id: str, actor_instance=None) -> Union[dict, BaseModel]:
    """Process a request - passed to constructor as callable"""
    # Business logic here
    return {"status": "success", "result": "..."}
```

**Key Features:**
- Both interfaces support Pydantic model validation
- `process_function` can optionally receive the actor instance for SYNC publishing
- Automatic type conversion between dict and Pydantic models
- Exception handling with automatic error response publishing


### Example: Passing `process_function` to the Actor Constructor
```python
def process_test_object(request_data: TestObject, request_id: str, actor_instance=None) -> ResponseObject:
    # some lines of implementation

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
```




## 2. MQTT Topic Paradigm

### Request Topics (Incoming)
- `REQ/ALL/{service_name}` - Broadcast requests to all instances
- `REQ/{hostname}/{service_name}` - Targeted requests to specific host

### Response Topics (Outgoing)
- `RESP/{hostname}/{service_name}/{request_id}/{stage}/{format}`
  - `stage`: ACK, RESULT, STATUS
  - `format`: JSON, EMOJI

### SYNC Topics (File Notifications)
- `SYNC/{hostname}@{hostname}:` - File availability notifications

**Response Flow:**
1. **ACK** - Immediate acknowledgment of request receipt
2. **STATUS** - Optional progress updates during processing
3. **RESULT** - Final success/error response with data

**Dual Format Publishing:**
- JSON responses contain structured data
- EMOJI responses provide visual status indicators (📥 ✅ ❌ ⏳ 🚀 ⚙️ 🎉 ⏹️)
