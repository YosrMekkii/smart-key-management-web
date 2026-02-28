"""
MQTT Relay: bridges RFID scan messages from Mosquitto to RabbitMQ.

Subscribes to the local Mosquitto broker on topic 'rfid/scan' and
republishes each received message to RabbitMQ via its MQTT plugin.
This works around compatibility issues with the built-in
Mosquitto-RabbitMQ bridge configuration.

Usage:
    python mqtt_relay.py

Environment variables (all optional, defaults shown):
    MOSQUITTO_HOST  – hostname of the local Mosquitto broker  (default: localhost)
    MOSQUITTO_PORT  – port of the local Mosquitto broker      (default: 1883)
    RABBITMQ_HOST   – hostname of the RabbitMQ broker         (default: localhost)
    RABBITMQ_PORT   – port of the RabbitMQ MQTT plugin        (default: 1883)
    RABBITMQ_USER   – RabbitMQ username                       (default: guest)
    RABBITMQ_PASS   – RabbitMQ password                       (default: guest)
    RFID_TOPIC      – MQTT topic to relay                     (default: rfid/scan)
"""

import json
import logging
import os

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (overridable via environment variables)
# ---------------------------------------------------------------------------
MOSQUITTO_HOST = os.environ.get("MOSQUITTO_HOST", "localhost")
MOSQUITTO_PORT = int(os.environ.get("MOSQUITTO_PORT", 1883))

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 1883))
RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.environ.get("RABBITMQ_PASS", "guest")

RFID_TOPIC = os.environ.get("RFID_TOPIC", "rfid/scan")

# ---------------------------------------------------------------------------
# RabbitMQ (destination) client
# ---------------------------------------------------------------------------
rabbitmq_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION1, client_id="relay-rabbitmq-publisher"
)
rabbitmq_client.username_pw_set(RABBITMQ_USER, RABBITMQ_PASS)


def _connect_rabbitmq():
    try:
        rabbitmq_client.connect(RABBITMQ_HOST, RABBITMQ_PORT, keepalive=60)
    except OSError as exc:
        logger.error(
            "Cannot connect to RabbitMQ at %s:%s – %s", RABBITMQ_HOST, RABBITMQ_PORT, exc
        )
        raise
    rabbitmq_client.loop_start()
    logger.info("Connected to RabbitMQ MQTT at %s:%s", RABBITMQ_HOST, RABBITMQ_PORT)


# ---------------------------------------------------------------------------
# Mosquitto (source) client callbacks
# ---------------------------------------------------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(
            "Connected to Mosquitto at %s:%s – subscribing to '%s'",
            MOSQUITTO_HOST,
            MOSQUITTO_PORT,
            RFID_TOPIC,
        )
        client.subscribe(RFID_TOPIC)
    else:
        logger.error("Failed to connect to Mosquitto, return code %s", rc)


def on_message(client, userdata, msg):
    payload_str = msg.payload.decode("utf-8")
    logger.info("Received on '%s': %s", msg.topic, payload_str)

    try:
        payload = json.loads(payload_str)
        if "tag_id" not in payload:
            logger.warning("Payload missing 'tag_id' field – forwarding anyway")
    except json.JSONDecodeError:
        logger.warning("Payload is not valid JSON – forwarding as-is")

    result = rabbitmq_client.publish(RFID_TOPIC, payload_str, qos=1)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        logger.info("Forwarded to RabbitMQ (mid=%s)", result.mid)
    else:
        logger.error("Failed to publish to RabbitMQ, rc=%s", result.rc)


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning("Unexpected disconnect from Mosquitto (rc=%s) – reconnecting…", rc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    _connect_rabbitmq()

    mosquitto_client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION1, client_id="relay-mosquitto-subscriber"
    )
    mosquitto_client.on_connect = on_connect
    mosquitto_client.on_message = on_message
    mosquitto_client.on_disconnect = on_disconnect

    try:
        mosquitto_client.connect(MOSQUITTO_HOST, MOSQUITTO_PORT, keepalive=60)
    except OSError as exc:
        logger.error(
            "Cannot connect to Mosquitto at %s:%s – %s", MOSQUITTO_HOST, MOSQUITTO_PORT, exc
        )
        rabbitmq_client.loop_stop()
        rabbitmq_client.disconnect()
        raise

    logger.info("Relay running – press Ctrl+C to stop")
    try:
        mosquitto_client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Relay stopped by user")
    finally:
        mosquitto_client.disconnect()
        rabbitmq_client.loop_stop()
        rabbitmq_client.disconnect()


if __name__ == "__main__":
    main()
