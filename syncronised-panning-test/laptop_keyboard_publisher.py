# laptop_keyboard_publisher.py
import json, time, argparse
from pynput import keyboard
import paho.mqtt.client as mqtt

def build_payload(cmd: str, delay_sec: float):
    now = time.time()
    return {
        "cmd": cmd,
        "execute_at": now + delay_sec,  # schedule a little in the future
        "sent_at": now,
        "sender": "laptop"
    }

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[*] Connected to MQTT at {userdata['broker']}:{userdata['port']}.")
    else:
        print(f"[!] Connect failed: rc={rc}")

def on_disconnect(client, userdata, rc, properties=None):
    print("[!] Disconnected. Reconnecting…")

def publisher_loop(broker, port, topic, delay):
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="kb-publisher",
        userdata={"broker": broker, "port": port}
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(broker, port, keepalive=60)
    client.loop_start()

    print("\n--- Keyboard controls ---")
    print("[Enter]  -> start")
    print("[a]      -> left")
    print("[d]      -> right")
    print("[q]      -> quit")
    print("-------------------------\n")

    def handle_key(key):
        try:
            if key == keyboard.Key.enter:
                payload = build_payload("start", delay)
            elif hasattr(key, 'char') and key.char in ('a', 'd', 'q'):
                if key.char == 'q':
                    print("[*] Quitting…")
                    client.loop_stop()
                    client.disconnect()
                    return False
                payload = build_payload("left" if key.char == 'a' else "right", delay)
            else:
                return True  # ignore

            client.publish(topic, json.dumps(payload), qos=1, retain=False)
            eta = time.strftime("%H:%M:%S", time.localtime(payload["execute_at"]))
            print(f"[->] {payload['cmd']} scheduled at {eta} (epoch {payload['execute_at']:.3f})")
            return True
        except Exception as e:
            print(f"[!] Key handler error: {e}")
            return True

    with keyboard.Listener(on_press=handle_key) as listener:
        listener.join()

def main():
    ap = argparse.ArgumentParser(description="Laptop keyboard → MQTT publisher")
    ap.add_argument("--broker", required=True, help="Broker host/IP (Pi #1 IP)")
    ap.add_argument("--port", type=int, default=1883, help="Broker port (default 1883)")
    ap.add_argument("--topic", default="audio/pan/cmd", help="MQTT topic")
    ap.add_argument("--delay", type=float, default=0.5, help="Seconds to schedule in the future")
    args = ap.parse_args()
    publisher_loop(args.broker, args.port, args.topic, args.delay)

if __name__ == "__main__":
    main()


## to run:
# python3 -m pip install paho-mqtt pynput
# python3 laptop_keyboard_publisher.py --broker 172.20.10.9 --port 1883

