---
title: MQTT Actor Demo
description: A comprehensive demonstration of function-based MQTT actors processing structured data requests.
---


# MQTT Actor Demo

This demo showcases a **function-based MQTT actor** that processes structured data requests over MQTT.

## What it does

- **Actor**: A `test-object-printer` service that receives `TestObject` requests via MQTT
- **Processing**: Writes each request to a timestamped JSON file in `./prints/`
- **Response**: Returns a `ResponseObject` with status and file path
- **Sync**: Publishes SYNC notices for external monitoring

## Architecture

- **MQTT Broker**: EMQX running on port 1883
- **Actor**: Function-based implementation using `MQTTActorShim`
- **Test Client**: Publishes test requests every 2 seconds
- **Subscribers**: Monitor responses and sync messages

## Key Features

- **Function-based**: No subclassing required - just pass a function to the constructor
- **Schema Validation**: Automatic Pydantic validation of requests/responses
- **Dockerized**: Complete containerized setup with health checks
- **Multi-format**: Supports JSON and EMOJI response formats
- **Monitoring**: Real-time visibility into all MQTT traffic

## Usage

```bash
./DEMO.sh  # Starts the complete demo environment
```

The demo runs continuously, processing test objects and demonstrating the MQTT actor pattern in action.
