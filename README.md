# smart-key-management-web

## MQTT Relay — Mosquitto → RabbitMQ bridge

`mqtt_relay.py` is a Python script that bridges RFID scan messages from a
local **Mosquitto** broker to **RabbitMQ** (via its MQTT plugin).  It works
around compatibility issues with the built-in Mosquitto-RabbitMQ bridge by
acting as an explicit subscriber/publisher.

### Architecture

```
RFID Reader
    │  MQTT publish  rfid/scan
    ▼
Mosquitto (port 1883)
    │  subscribed by mqtt_relay.py
    ▼
mqtt_relay.py  ──MQTT publish rfid/scan──▶  RabbitMQ MQTT plugin (port 1883)
```

### Prerequisites

```bash
pip install paho-mqtt
```

### Running the relay

```bash
python mqtt_relay.py
```

Configuration is done via environment variables:

| Variable         | Default     | Description                              |
|------------------|-------------|------------------------------------------|
| `MOSQUITTO_HOST` | `localhost` | Hostname of the local Mosquitto broker   |
| `MOSQUITTO_PORT` | `1883`      | Port of the local Mosquitto broker       |
| `RABBITMQ_HOST`  | `localhost` | Hostname of the RabbitMQ broker          |
| `RABBITMQ_PORT`  | `1883`      | Port of the RabbitMQ MQTT plugin         |
| `RABBITMQ_USER`  | `guest`     | RabbitMQ username                        |
| `RABBITMQ_PASS`  | `guest`     | RabbitMQ password                        |
| `RFID_TOPIC`     | `rfid/scan` | MQTT topic to relay                      |

### Testing with test_pub.py

`test_pub.py` publishes a sample RFID scan payload to Mosquitto so the relay
pipeline can be verified without real hardware:

```bash
python test_pub.py --tag TEST123
```

The script accepts `--host`, `--port`, and `--tag` flags (all optional).

A payload like the following is sent:

```json
{"tag_id": "TEST123", "timestamp": 1234567890}
```
