# rpi_broker_host.py
import subprocess, shutil, sys, tempfile, textwrap, os

def main():
    exe = shutil.which("mosquitto")
    if not exe:
        print("[!] mosquitto not found. Install with: sudo apt install -y mosquitto")
        sys.exit(1)

    conf = textwrap.dedent("""\
        listener 1883 0.0.0.0
        allow_anonymous true
        persistence false
    """)

    with tempfile.NamedTemporaryFile("w", delete=False, prefix="mosq_", suffix=".conf") as f:
        f.write(conf)
        cfg_path = f.name

    print(f"[*] Starting mosquitto with {cfg_path}")
    print("[*] Press Ctrl+C to stop.")
    try:
        subprocess.run([exe, "-c", cfg_path], check=False)
    finally:
        try:
            os.remove(cfg_path)
        except OSError:
            pass

if __name__ == "__main__":
    main()



# Rpi 1 must open two seprate terminals:

# # Terminal A: broker host
# python3 rpi_broker_host.py

# # Terminal B: subscriber
# python3 rpi_listener.py --id 1 --broker 127.0.0.1 --audio /syncronised-panning-test/smooth-ac-guitar-loop.mp3
