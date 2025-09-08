FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    mosquitto-clients \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY py_mqtt_actor.py .
COPY INTERFACE.py .
COPY function-based-actor.py .

# Create prints directory for output files
RUN mkdir -p /app/prints

# Make the script executable
RUN chmod +x function-based-actor.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MQTT_BROKER=emqx
ENV MQTT_PORT=1883

# Expose any ports if needed (MQTT client doesn't need exposed ports)
# EXPOSE 1883

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD mosquitto_pub -h $MQTT_BROKER -p $MQTT_PORT -t "HEALTH/function-based-actor" -m "ping" || exit 1

# Run the function-based actor
CMD ["python", "function-based-actor.py", "--mqtt-broker", "emqx", "--mqtt-port", "1883"]
