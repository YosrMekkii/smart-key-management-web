"""
Test publisher: sends a sample RFID scan JSON message to Mosquitto.

Used to verify the mqtt_relay.py pipeline end-to-end without needing
real RFID hardware.

Usage:
    python test_pub.py [--host HOST] [--port PORT] [--tag TAG_ID]

Defaults:
    --host  localhost
    --port  1883
    --tag   TEST123
"""

import argparse
import json
import time

import paho.mqtt.client as mqtt

RFID_TOPIC = "rfid/scan"


def parse_args():
    parser = argparse.ArgumentParser(description="Publish a test RFID scan message to Mosquitto.")
    parser.add_argument("--host", default="localhost", help="Mosquitto broker hostname")
    parser.add_argument("--port", type=int, default=1883, help="Mosquitto broker port")
    parser.add_argument("--tag", default="TEST123", help="RFID tag ID to include in the payload")
    return parser.parse_args()


def main():
    args = parse_args()

    payload = json.dumps({"tag_id": args.tag, "timestamp": int(time.time())})

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="test-publisher")
    try:
        client.connect(args.host, args.port, keepalive=60)
    except OSError as exc:
        print(f"Error: cannot connect to Mosquitto at {args.host}:{args.port} – {exc}")
        raise SystemExit(1) from exc

    result = client.publish(RFID_TOPIC, payload, qos=1)
    result.wait_for_publish()

    print(f"Published to '{RFID_TOPIC}': {payload}")

    client.disconnect()


if __name__ == "__main__":
    main()
