#!/usr/bin/env python3
"""
# Generalized MQTT Actor Shim


Astro Docs: http://localhost:4322/spec/py_mqtt_actor/


This module provides a base class for creating MQTT-based actors that follow the
standard request-response pattern used across the PhotogrammetryWAAM system.

Each actor:
1. Subscribes to REQ/{recipient}/{service_name} topics (optionally with UUID: REQ/{recipient}/{service_name}/{uuid})
2. Processes requests in background threads
3. Publishes both EMOJI and JSON responses to RESP/{hostname}/{service_name}/{request_id}/{stage}/{format}
4. Handles errors consistently
5. Supports both targeted and broadcast requests
6. Uses provided UUID from request topic or generates one if not present

Usage:
    class MyActor(MQTTActorShim):
        def __init__(self, mqtt_broker: str, mqtt_port: int = 1883):
            super().__init__(
                service_name="my-service",
                mqtt_broker=mqtt_broker,
                mqtt_port=mqtt_port,
                request_schema=MyRequestSchema,
                response_schema=MyResponseSchema
            )
        
        def process_request(self, request_data: dict, request_id: str) -> dict:
            # Implement your business logic here
            return {"status": "success", "result": "..."}
"""

import json
import time
import os
import socket
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Type, Union, Callable
import argparse
import logging

import paho.mqtt.client as mqtt
from pydantic import BaseModel, ValidationError


class MQTTActorShim(ABC):
    """
    Base class for MQTT-based actors following the standard request-response pattern.
    
    This shim handles:
    - MQTT connection management
    - Topic subscription and publishing
    - Request validation using Pydantic schemas
    - Background request processing
    - Consistent error handling and response formatting
    - Both EMOJI and JSON response publishing
    """
    
    def __init__(
        self,
        service_name: str,
        mqtt_broker: str,
        mqtt_port: int = 1883,
        request_schema: Optional[Type[BaseModel]] = None,
        response_schema: Optional[Type[BaseModel]] = None,
        host_interface: str = "eth0",
        log_level: str = "INFO",
        process_function: Optional[Callable[..., dict]] = None
    ):
        """
        Initialize the MQTT Actor Shim.
        
        Args:
            service_name: Name of the service (e.g., "capture-single-frame", "focus-stack")
            mqtt_broker: MQTT broker address
            mqtt_port: MQTT broker port
            request_schema: Pydantic model for validating incoming requests
            response_schema: Pydantic model for validating outgoing responses
            host_interface: Network interface to use for hostname detection
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            process_function: Optional function to process requests instead of subclass method
        """
        self.service_name = service_name
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.request_schema = request_schema
        self.response_schema = response_schema
        self.host_interface = host_interface
        self.process_function = process_function
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=f'%(asctime)s - {service_name} - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(f"py_mqtt_actor.{service_name}")
        
        # Get hostname for topic routing
        self.hostname = self.get_hostname()
        
        # MQTT topics - REQ/RESP format
        self.request_topics = [
            f"REQ/ALL/{self.service_name}/#",
            f"REQ/{self.hostname}/{self.service_name}/#"
        ]
        
        # MQTT client setup
        self.client = mqtt.Client(protocol=mqtt.MQTTv5)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Track active requests
        self.active_requests: Dict[str, threading.Thread] = {}
        
        self.logger.info(f"MQTT Actor '{service_name}' initialized")
        self.logger.info(f"Hostname: {self.hostname}")
        self.logger.info(f"Host interface: {self.host_interface}")
        self.logger.info(f"MQTT Broker: {mqtt_broker}:{mqtt_port}")
        self.logger.info(f"Will subscribe to: {', '.join(self.request_topics)}")
        self.logger.info(f"Will respond on: RESP/{self.hostname}/{self.service_name}/{{request_id}}/{{stage}}/{{format}}")

    def get_hostname(self) -> str:
        """Get the hostname of this device"""
        try:
            return socket.gethostname()
        except Exception as e:
            self.logger.error(f"Error getting hostname: {e}")
            return "unknown-host"

    def get_current_user(self) -> str:
        """Get the current username"""
        try:
            import subprocess
            result = subprocess.run(
                ["whoami"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))

    def on_connect(self, client, userdata, flags, reasonCode, properties=None):
        """Callback for when the client receives a CONNACK response (MQTT v5 compatible)."""
        try:
            rc = int(reasonCode) if reasonCode is not None else 0
        except Exception:
            rc = reasonCode

        if rc == 0:
            self.logger.info(f"Connected to MQTT broker with result code {rc}")
            for topic in self.request_topics:
                client.subscribe(topic)
                self.logger.info(f"Subscribed to {topic}")
        else:
            self.logger.error(f"Failed to connect to MQTT broker with result code {rc}")

    def on_message(self, client, userdata, msg):
        """Callback for when a PUBLISH message is received from the server"""
        try:
            # Expected topic formats: 
            # REQ/<recipient>/<service_name> or REQ/<recipient>/<service_name>/<uuid>
            topic_parts = msg.topic.split('/')
            if len(topic_parts) < 3 or len(topic_parts) > 4 or topic_parts[0] != "REQ" or topic_parts[2] != self.service_name:
                self.logger.warning(f"Invalid topic format: {msg.topic}")
                return

            _, recipient, _service = topic_parts[:3]
            request_id = topic_parts[3] if len(topic_parts) == 4 else None

            # Check if this message is for us
            if recipient != "ALL" and recipient != self.hostname:
                self.logger.debug(f"Message for {recipient}, ignoring (our hostname: {self.hostname})")
                return

            self.logger.info(f"Processing REQ '{msg.topic}' for recipient '{recipient}' (our hostname: {self.hostname})")

            # Use provided request ID or generate one if not present
            if request_id is None:
                request_id = str(uuid.uuid4())[:8]
                self.logger.debug(f"Generated request ID: {request_id}")
            else:
                self.logger.debug(f"Using provided request ID: {request_id}")
            
            # Parse the JSON message body
            try:
                message = json.loads(msg.payload.decode())
                self.logger.info(f"Received {self.service_name} request: {message}")
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON in request: {e}"
                self.logger.error(error_msg)
                self.publish_error_response(request_id, error_msg)
                return

            # Validate request if schema is provided
            if self.request_schema:
                try:
                    validated_request = self.request_schema(**message)
                    message = validated_request.model_dump()
                except ValidationError as e:
                    error_msg = f"Request validation failed: {e}"
                    self.logger.error(error_msg)
                    self.publish_error_response(request_id, error_msg)
                    return

            # Process the request in a background thread
            thread = threading.Thread(
                target=self._process_request_wrapper,
                args=(message, request_id),
                daemon=True
            )
            self.active_requests[request_id] = thread
            thread.start()
            
        except Exception as e:
            error_msg = f"Error processing request: {e}"
            self.logger.error(error_msg)
            request_id = str(uuid.uuid4())[:8]
            self.publish_error_response(request_id, error_msg)

    def _process_request_wrapper(self, request_data: dict, request_id: str):
        """Wrapper for processing requests that handles cleanup and error handling"""
        try:
            # Send ACK response
            self.publish_ack_response(request_id, request_data)
            
            # Process the actual request
            result = self.process_request(request_data, request_id)
            
            # Send success response
            self.publish_success_response(request_id, result)
            
        except Exception as e:
            error_msg = f"Error during request processing: {e}"
            self.logger.error(error_msg)
            self.publish_error_response(request_id, error_msg)
        finally:
            # Clean up active request tracking
            if request_id in self.active_requests:
                del self.active_requests[request_id]

    def process_request(self, request_data: dict, request_id: str) -> dict:
        """
        Process a request. Uses process_function if provided, otherwise must be implemented by subclasses.
        
        Args:
            request_data: Validated request data as dict. If the provided
                process_function's first parameter is annotated with a
                Pydantic BaseModel type, this method will instantiate that
                model from request_data and pass the model instance instead.
            request_id: Unique identifier for this request
            
        Returns:
            dict: Response data to be sent back to the client
            
        Raises:
            Exception: Any exception will be caught and sent as an error response
        """
        if not self.process_function:
            raise NotImplementedError("Either provide process_function or implement process_request in subclass")

        import inspect
        typed_arg = request_data
        try:
            signature = inspect.signature(self.process_function)
            parameters = list(signature.parameters.values())
            expects_actor_instance = len(parameters) >= 3

            if parameters:
                first_param = parameters[0]
                annotation = first_param.annotation

                # If the first param is annotated with a Pydantic model, instantiate it from the dict
                if annotation is not inspect._empty:
                    try:
                        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                            typed_arg = annotation(**request_data)
                    except Exception:
                        # Fallback to dict if instantiation fails
                        typed_arg = request_data

            if expects_actor_instance:
                result = self.process_function(typed_arg, request_id, self)
            else:
                result = self.process_function(typed_arg, request_id)
            
            # Convert Pydantic model result to dict if needed
            if isinstance(result, BaseModel):
                return result.model_dump()
            return result
        except Exception:
            # As a last resort, call with raw dict
            try:
                result = self.process_function(request_data, request_id)
                if isinstance(result, BaseModel):
                    return result.model_dump()
                return result
            except Exception:
                result = self.process_function(request_data, request_id, self)
                if isinstance(result, BaseModel):
                    return result.model_dump()
                return result

    def publish_ack_response(self, request_id: str, request_data: dict):
        """Publish ACK response acknowledging receipt of request"""
        ack_data = {
            "status": "received",
            "timestamp": datetime.now().isoformat(),
            "hostname": self.hostname,
            "request_id": request_id,
            "service": self.service_name
        }
        
        # Add request data if it fits in ACK
        if len(str(request_data)) < 1000:  # Reasonable size limit for ACK
            ack_data["request"] = request_data
        
        self.publish_response("ACK", ack_data, request_id)

    def publish_success_response(self, request_id: str, result_data: dict):
        """Publish success response with result data"""
        success_data = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "hostname": self.hostname,
            "request_id": request_id,
            "service": self.service_name,
            **result_data
        }
        
        self.publish_response("RESULT", success_data, request_id)

    def publish_error_response(self, request_id: str, error_message: str):
        """Publish error response"""
        error_data = {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "hostname": self.hostname,
            "request_id": request_id,
            "service": self.service_name,
            "error": error_message
        }
        
        self.publish_response("RESULT", error_data, request_id)

    def publish_status_response(self, request_id: str, status_data: dict):
        """Publish status update response"""
        status_data = {
            "status": "status",
            "timestamp": datetime.now().isoformat(),
            "hostname": self.hostname,
            "request_id": request_id,
            "service": self.service_name,
            **status_data
        }
        
        self.publish_response("STATUS", status_data, request_id)

    def publish_response(self, stage: str, data: dict, request_id: str):
        """Publish both EMOJI and JSON responses"""
        # Validate response if schema is provided
        if self.response_schema:
            try:
                validated_response = self.response_schema(**data)
                data = validated_response.model_dump()
            except ValidationError as e:
                self.logger.error(f"Response validation failed: {e}")
                # Fall back to original data if validation fails
                pass

        # Publish JSON response
        self.publish_json_response(stage, data, request_id)
        
        # Publish EMOJI response
        emoji = self.get_emoji_for_status(data.get("status", "unknown"))
        self.publish_emoji_response(stage, emoji, request_id)

    def publish_json_response(self, stage: str, data: dict, request_id: str):
        """Publish JSON response to MQTT"""
        json_topic = f"RESP/{self.hostname}/{self.service_name}/{request_id}/{stage}/JSON"
        
        try:
            json_payload = json.dumps(data, indent=2)
            result = self.client.publish(json_topic, json_payload)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"Published JSON response to {json_topic}")
            else:
                self.logger.error(f"Failed to publish JSON response: {result.rc}")
        except Exception as e:
            self.logger.error(f"Error publishing JSON response: {e}")

    def publish_emoji_response(self, stage: str, emoji: str, request_id: str):
        """Publish emoji response to MQTT"""
        emoji_topic = f"RESP/{self.hostname}/{self.service_name}/{request_id}/{stage}/EMOJI"
        
        result = self.client.publish(emoji_topic, emoji)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self.logger.debug(f"Published emoji '{emoji}' to {emoji_topic}")
        else:
            self.logger.error(f"Failed to publish emoji '{emoji}': {result.rc}")

    def get_emoji_for_status(self, status: str) -> str:
        """Get appropriate emoji for status"""
        emoji_map = {
            "received": "📥",
            "success": "✅",
            "error": "❌",
            "status": "⏳",
            "starting": "🚀",
            "processing": "⚙️",
            "completed": "🎉",
            "cancelled": "⏹️"
        }
        return emoji_map.get(status, "❓")

    def publish_sync_notice(self, filepath: Union[str, Path], session_id: Optional[str] = None):
        """Publish SYNC notice for file availability"""
        username = self.get_current_user()
        sync_topic = f"SYNC/{self.hostname}@{self.hostname}:"
        
        # Include session_id in payload if provided
        payload = str(filepath)
        if session_id:
            payload = f"{session_id}:{payload}"
        
        result = self.client.publish(sync_topic, payload)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self.logger.info(f"Published SYNC notice to {sync_topic} with payload: {payload}")
        else:
            self.logger.error(f"Failed to publish SYNC notice: {result.rc}")

    def start(self):
        """Start the MQTT actor"""
        try:
            self.logger.info(f"Connecting to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            self.client.connect(self.mqtt_broker, self.mqtt_port)
            
            self.logger.info("Starting MQTT loop...")
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            self.logger.info("\nShutting down MQTT Actor...")
        except Exception as e:
            self.logger.error(f"Error in MQTT server: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        # Wait for active requests to complete (with timeout)
        for request_id, thread in list(self.active_requests.items()):
            if thread.is_alive():
                self.logger.info(f"Waiting for request {request_id} to complete...")
                thread.join(timeout=5.0)
                if thread.is_alive():
                    self.logger.warning(f"Request {request_id} did not complete within timeout")
        
        self.client.disconnect()
        self.logger.info("MQTT client disconnected")

    def get_active_request_count(self) -> int:
        """Get the number of currently active requests"""
        return len([t for t in self.active_requests.values() if t.is_alive()])


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

class ExampleRequestSchema(BaseModel):
    """Example request schema"""
    message: str
    delay_seconds: int = 0

class ExampleResponseSchema(BaseModel):
    """Example response schema"""
    status: str
    result: str
    processed_at: str

class ExampleActor(MQTTActorShim):
    """Example actor implementation"""
    
    def __init__(self, mqtt_broker: str, mqtt_port: int = 1883):
        super().__init__(
            service_name="example-service",
            mqtt_broker=mqtt_broker,
            mqtt_port=mqtt_port,
            request_schema=ExampleRequestSchema,
            response_schema=ExampleResponseSchema
        )
    
    def process_request(self, request_data: dict, request_id: str) -> dict:
        """Process an example request"""
        message = request_data["message"]
        delay_seconds = request_data.get("delay_seconds", 0)
        
        # Simulate processing time
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        
        return {
            "result": f"Processed: {message}",
            "processed_at": datetime.now().isoformat(),
            "delay_applied": delay_seconds
        }


def main():
    """Example main function"""
    parser = argparse.ArgumentParser(description="Example MQTT Actor")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    try:
        actor = ExampleActor(
            mqtt_broker=args.mqtt_broker,
            mqtt_port=args.mqtt_port
        )
        actor.start()
    except Exception as e:
        print(f"Failed to start actor: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
