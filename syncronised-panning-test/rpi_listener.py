#!/usr/bin/env python3
import argparse, json, time, subprocess, shutil, sys, re
import paho.mqtt.client as mqtt

TOPIC = "audio/pan/cmd"
VOLUME_STEP = 10

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def amixer_set(vol_percent: int, mixer: str):
    """Set volume for the given mixer control (e.g. Headphones, Master)."""
    vol_percent = max(0, min(100, vol_percent))
    r = run(["amixer", "-M", "sset", mixer, f"{vol_percent}%", "unmute"])
    return r.returncode == 0

def amixer_get(mixer: str):
    """Get current volume % for a given mixer control."""
    r = run(["amixer", "-M", "sget", mixer])
    m = re.search(r"\[(\d{1,3})%\]", r.stdout)
    return int(m.group(1)) if m else None

class Player:
    def __init__(self, audio_file: str, sink: str, alsa_device: str | None):
        self.audio_file = audio_file
        self.sink = sink
        self.alsa_device = alsa_device
        self.proc = None

    def is_running(self):
        return (self.proc is not None) and (self.proc.poll() is None)

    def start(self):
        if self.is_running():
            return
        if not shutil.which("mpg123"):
            print("[!] mpg123 not found. Install it with: sudo apt install mpg123")
            return
        cmd = ["mpg123", "-q"]
        if self.sink == "pulse":
            cmd += ["-o", "pulse"]
        elif self.sink == "alsa" and self.alsa_device:
            cmd += ["-a", self.alsa_device]
        cmd += [self.audio_file]
        print(f"[*] Launching player: {' '.join(cmd)}")
        self.proc = subprocess.Popen(cmd)

    def stop(self):
        if self.is_running():
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

def schedule_execute(execute_at: float, fn):
    delay = execute_at - time.time()
    if delay > 0: time.sleep(delay)
    fn()

def handle_cmd(pi_id: int, cmd: str, player: Player, mixer: str):
    current = amixer_get(mixer)
    if current is None: current = 70

    if cmd == "start":
        amixer_set(70, mixer)
        player.start()
        print(f"[{pi_id}] start -> volume=70% ({mixer}), playing {player.audio_file}")
        return

    if cmd not in ("left", "right"):
        print(f"[{pi_id}] Unknown cmd: {cmd}"); return

    delta = +VOLUME_STEP if (cmd=="left" and pi_id==1) or (cmd=="right" and pi_id==2) else -VOLUME_STEP
    new_vol = max(0, min(100, current + delta))
    if amixer_set(new_vol, mixer):
        print(f"[{pi_id}] {cmd} -> {mixer}: {current}% -> {new_vol}%")
    else:
        print(f"[{pi_id}] Could not set volume via amixer on '{mixer}'.")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[*] Connected to broker.")
        client.subscribe(TOPIC, qos=1)
        print(f"[*] Subscribed to {TOPIC}")
    else:
        print(f"[!] Connect failed rc={rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        cmd = payload.get("cmd")
        execute_at = float(payload.get("execute_at", time.time()))
        eta_str = time.strftime("%H:%M:%S", time.localtime(execute_at))
        print(f"[->] {cmd} scheduled for {eta_str} (epoch {execute_at:.3f})")

        schedule_execute(execute_at,
            lambda: handle_cmd(userdata["pi_id"], cmd, userdata["player"], userdata["mixer"]))
    except Exception as e:
        print(f"[!] Message handling error: {e}")

def main():
    ap = argparse.ArgumentParser(description="RPi synchronized audio panner")
    ap.add_argument("--id", type=int, required=True, choices=[1, 2], help="RPi ID (1=left, 2=right)")
    ap.add_argument("--broker", required=True, help="MQTT broker host/IP")
    ap.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    ap.add_argument("--audio", required=True, help="Path to audio file (mp3)")
    ap.add_argument("--sink", choices=["pulse","alsa"], default="alsa", help="Audio backend for mpg123")
    ap.add_argument("--alsa-device", default=None, help="ALSA device name (e.g., plughw:0,0)")
    ap.add_argument("--mixer", default="Headphones", help="Mixer control (Headphones, Master, PCM, etc.)")
    args = ap.parse_args()

    player = Player(args.audio, sink=args.sink, alsa_device=args.alsa_device)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"rpi-{args.id}",
                         userdata={"pi_id": args.id, "player": player, "mixer": args.mixer})
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, keepalive=60)

    print(f"[*] RPi ID={args.id}. Broker={args.broker}:{args.port}")
    print(f"[*] Using sink={args.sink}, mixer={args.mixer}, audio={args.audio}")
    print("[*] Ensure system time is NTP-synced.")
    client.loop_forever()

if __name__ == "__main__":
    main()



# sudo apt update
# sudo apt install -y python3-pip mpg123 alsa-utils paho-mqtt mosquitto mosquitto-clients


## to run:
# # On Pi #1 (left + broker host)
# python3 rpi_listener.py --id 1 --broker 127.20.10.9 --audio /syncronised-panning-test/smooth-ac-guitar-loop.mp3

# # On Pi #2 (right)
# python3 rpi_listener.py --id 2 --broker 172.20.10.9 --audio /syncronised-panning-test/smooth-ac-guitar-loop.mp3



## to run (new) Rpi1:
# python3 rpi_listener.py --id 1 \
#   --broker 127.0.0.1 \
#   --sink pulse \
#   --mixer Master \
#   --audio /home/pi/music/smooth-acoustic-loop.mp3