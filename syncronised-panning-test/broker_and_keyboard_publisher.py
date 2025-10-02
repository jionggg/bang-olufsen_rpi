# broker_and_keyboard_publisher.py
import json, time, shutil, subprocess, sys, signal
from pathlib import Path
from threading import Thread
from pynput import keyboard
import paho.mqtt.client as mqtt

BROKER_HOST = "172.0.0.1" #"127.0.0.1"
BROKER_PORT = 1883
TOPIC = "audio/pan/cmd"
KEY_DELAY_SEC = 0.5

def maybe_launch_mosquitto():
    """
    Launch mosquitto as a subprocess if available.
    Looks for 'mosquitto' in PATH and uses a temp in-memory conf if needed.
    """
    exe = shutil.which("mosquitto")
    if not exe:
        print("[!] Mosquitto not found in PATH. Install it, or run your own broker.")
        return None

    # Minimal config: default listener on 1883, allow anonymous on LAN
    conf = (
        "listener 1883 0.0.0.0\n"
        "allow_anonymous true\n"
        "# persistence false\n"
    )
    cfg_path = Path.cwd() / "tmp_mosquitto.conf"
    cfg_path.write_text(conf)
    print(f"[*] Launching mosquitto broker: {exe} -c {cfg_path}")
    proc = subprocess.Popen([exe, "-c", str(cfg_path)])
    return proc

def build_payload(cmd: str):
    now = time.time()
    payload = {
        "cmd": cmd,
        "execute_at": now + KEY_DELAY_SEC,  # schedule in the future
        "sent_at": now,
        "sender": "laptop"
    }
    return payload

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[*] Publisher connected to MQTT.")
    else:
        print(f"[!] Publisher connection failed: rc={rc}")

def publisher_loop():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="kb-publisher")
    client.on_connect = on_connect
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
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
                payload = build_payload("start")
            elif hasattr(key, 'char') and key.char in ('a', 'd', 'q'):
                if key.char == 'q':
                    print("[*] Quitting...")
                    client.loop_stop()
                    client.disconnect()
                    return False
                payload = build_payload("left" if key.char == 'a' else "right")
            else:
                return True  # ignore

            msg = json.dumps(payload)
            client.publish(TOPIC, msg, qos=1, retain=False)
            eta = time.strftime("%H:%M:%S", time.localtime(payload["execute_at"]))
            print(f"[->] {payload['cmd']} scheduled at {eta} (epoch {payload['execute_at']:.3f})")
            return True
        except Exception as e:
            print(f"[!] Key handler error: {e}")
            return True

    with keyboard.Listener(on_press=handle_key) as listener:
        listener.join()

def main():
    broker_proc = maybe_launch_mosquitto()
    try:
        publisher_loop()
    finally:
        if broker_proc:
            print("[*] Stopping broker...")
            try:
                broker_proc.send_signal(signal.SIGTERM)
                broker_proc.wait(timeout=3)
            except Exception:
                broker_proc.kill()

if __name__ == "__main__":
    main()


## to run:
# python broker_and_keyboard_publisher.py

#Press Enter/a/d to broadcast; each message carries an execute_at = now + 0.5s.