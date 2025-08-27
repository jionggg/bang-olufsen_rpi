#!/usr/bin/env python3
# slave.py — publish JSON to house/anchors/<device_id> via master broker
import json, time, os
from datetime import datetime
from paho.mqtt import client as mqtt

DEVICE_ID = input("Enter device_id for SLAVE: ").strip() or "slave-1"
BROKER_HOST = input("Enter MASTER broker IP: ").strip() or "192.168.1.10"
BROKER_PORT = 1883
TOPIC_BASE = "house/anchors"

pub_hz = float(os.getenv("PUB_HZ", "2"))

def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected" if rc == 0 else f"Connect failed rc={rc}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"pub-{DEVICE_ID}")
client.on_connect = on_connect
client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
client.loop_start()

topic = f"{TOPIC_BASE}/{DEVICE_ID}"
print(f"Publishing to '{topic}' at {pub_hz} Hz via {BROKER_HOST}. Ctrl+C to stop.")
try:
    n = 0
    period = 1.0 / pub_hz
    while True:
        payload = {
            "device_id": DEVICE_ID,
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "seq": n
        }
        client.publish(topic, json.dumps(payload), qos=0, retain=False)
        n += 1
        time.sleep(period)
except KeyboardInterrupt:
    pass
finally:
    client.loop_stop()
    client.disconnect()
