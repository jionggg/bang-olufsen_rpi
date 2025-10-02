# rpi_listener.py
import argparse, json, time, subprocess, shutil, sys, re
import paho.mqtt.client as mqtt

TOPIC = "audio/pan/cmd"
DEFAULT_BROKER = "192.168.1.100"  # override with --broker
AUDIO_FILE_DEFAULT = "/home/pi/music/track.mp3"
VOLUME_STEP = 10

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def amixer_set(vol_percent: int):
    """Try several controls to set volume; ignore errors and stop at first success."""
    vol_percent = max(0, min(100, vol_percent))
    controls = ["Headphone", "Master", "PCM", "Digital"]
    for ctl in controls:
        r = run(["amixer", "sset", ctl, f"{vol_percent}%"])
        if r.returncode == 0:
            return True
    return False

def amixer_get():
    """Best-effort parse of current volume from amixer."""
    controls = ["Headphone", "Master", "PCM", "Digital"]
    vol = None
    for ctl in controls:
        r = run(["amixer", "sget", ctl])
        if r.returncode != 0:
            continue
        m = re.search(r"\[(\d{1,3})%\]", r.stdout)
        if m:
            vol = int(m.group(1))
            break
    return vol

class Player:
    def __init__(self, audio_file: str):
        self.audio_file = audio_file
        self.proc = None

    def is_running(self):
        return (self.proc is not None) and (self.proc.poll() is None)

    def start(self):
        if self.is_running():
            return
        if not shutil.which("mpg123"):
            print("[!] mpg123 not found. Install it or change the player.")
            return
        # -q quiet, -l 0 loop forever
        self.proc = subprocess.Popen(["mpg123", "-q", "-l", "0", self.audio_file])

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
    if delay > 0:
        time.sleep(delay)
    fn()

def handle_cmd(pi_id: int, cmd: str, player: Player):
    # First-time volume if needed
    current = amixer_get()
    if current is None:
        current = 20  # fallback
    if cmd == "start":
        amixer_set(20)
        player.start()
        print(f"[{pi_id}] start -> volume=20%, playing {player.audio_file}")
        return

    # left/right panning rules
    delta = 0
    if cmd == "left":
        delta = +VOLUME_STEP if pi_id == 1 else -VOLUME_STEP
    elif cmd == "right":
        delta = -VOLUME_STEP if pi_id == 1 else +VOLUME_STEP
    else:
        print(f"[{pi_id}] Unknown cmd: {cmd}")
        return

    new_vol = max(0, min(100, current + delta))
    ok = amixer_set(new_vol)
    if not ok:
        print(f"[{pi_id}] Could not set volume via amixer.")
    else:
        print(f"[{pi_id}] {cmd} -> volume {current}% -> {new_vol}%")

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
        print(f"[->] Received {cmd}, scheduled for {eta_str} (epoch {execute_at:.3f})")

        schedule_execute(execute_at, lambda: handle_cmd(userdata["pi_id"], cmd, userdata["player"]))
    except Exception as e:
        print(f"[!] Message handling error: {e}")

def main():
    ap = argparse.ArgumentParser(description="RPi synchronized audio panner")
    ap.add_argument("--id", type=int, required=True, choices=[1, 2], help="RPi ID (1=left, 2=right)")
    ap.add_argument("--broker", default=DEFAULT_BROKER, help="MQTT broker host/IP")
    ap.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    ap.add_argument("--audio", default=AUDIO_FILE_DEFAULT, help="Path to audio file (mp3)")
    args = ap.parse_args()

    player = Player(args.audio)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"rpi-{args.id}", userdata={"pi_id": args.id, "player": player})
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, keepalive=60)

    print(f"[*] RPi ID={args.id}. Broker={args.broker}:{args.port}. Audio={args.audio}")
    print("[*] Ensure your system time is synced (NTP) for accurate scheduling.")
    client.loop_forever()

if __name__ == "__main__":
    main()



## to run:
# python3 rpi_listener.py --id 1 --broker <LAPTOP_IP> --audio /home/pi/music/track.mp3
# # in another terminal on the other Pi:
# python3 rpi_listener.py --id 2 --broker <LAPTOP_IP> --audio /home/pi/music/track.mp3
