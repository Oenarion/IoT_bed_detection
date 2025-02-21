# Use Ubuntu as the base image
FROM ubuntu:20.04

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Mosquitto and related utilities
RUN apt-get update && \
    apt-get install -y mosquitto mosquitto-clients sudo && \
    apt-get clean

# Create a directory for Mosquitto configuration if needed
RUN mkdir -p /mosquitto/config /mosquitto/data /mosquitto/log

# Copy the default Mosquitto configuration file
COPY mosquitto.conf /mosquitto/config/mosquitto.conf

# Copy the passwd file
#COPY passwd /mosquitto/config/passwd

# Expose port 1883 for MQTT and port 9001 for WebSockets (if needed)
EXPOSE 1883 9001

# Run Mosquitto in the foreground so Docker container stays running
CMD ["/usr/sbin/mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
