#!/usr/bin/env python3
# laptop_subscriber.py — subscribe to house/anchors/# and save JSON (paho v1.x)
import os, json, pathlib
from datetime import datetime
import paho.mqtt.client as mqtt

BROKER_HOST = input("Enter broker host (default mqtt-broker.local): ").strip() or "mqtt-broker.local"
BROKER_PORT = 1883
TOPIC = "house/anchors/#"
SAVE_DIR = pathlib.Path("./data/anchors")

def ensure_dir(p): p.mkdir(parents=True, exist_ok=True)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected. Subscribing to {TOPIC} ...")
        client.subscribe(TOPIC, qos=0)
    else:
        print(f"Connect failed rc={rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        device = str(payload.get("device_id", "unknown"))
        ts = datetime.now().strftime("%YMM%d_%H%M%S_%f")[:-3]  # filename timestamp
        folder = SAVE_DIR / device
        ensure_dir(folder)
        fname = folder / f"{ts}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        print(f"Saved: {fname}")
    except Exception as e:
        print(f"Bad message on {msg.topic}: {e}")

client = mqtt.Client(client_id="laptop-sub")  # v1.x style
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
print(f"Connecting to {BROKER_HOST}:{BROKER_PORT} ... Ctrl+C to quit.")
client.loop_forever()
