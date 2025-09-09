FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    mosquitto-clients \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire package (from project root context)
COPY . /app/package
WORKDIR /app/package

# Install the package in development mode
RUN pip install --no-cache-dir -e .

# Copy example files to app directory
WORKDIR /app
COPY example/INTERFACE.py .
COPY example/function-based-actor.py .

# Create prints directory for output files
RUN mkdir -p /app/prints

# Make the script executable
RUN chmod +x function-based-actor.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MQTT_BROKER=emqx
ENV MQTT_PORT=1883

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD mosquitto_pub -h $MQTT_BROKER -p $MQTT_PORT -t "HEALTH/function-based-actor" -m "ping" || exit 1

# Run the function-based actor
CMD ["python", "function-based-actor.py", "--mqtt-broker", "emqx", "--mqtt-port", "1883"]
