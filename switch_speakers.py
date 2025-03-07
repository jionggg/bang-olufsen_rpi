import subprocess
import time

# Define MAC addresses of your Bluetooth speakers
BT_SPEAKER_2 = "04:FE:A1:DB:7D:01"  # MAC of Beoplay P2
#BT_SPEAKER_1 = "172.31.62.25"  #MAc of my msi
BT_SPEAKER_1 = "20:18:5B:51:55:B7"  # MAC of NUSC JBL Flip 6


def run_command(command):
    """Run a shell command and return output."""
    process = subprocess.run(command, shell=True, capture_output=True, text=True)
    return process.stdout.strip()

def connect_bluetooth_device(mac_address):
    """Connect to a Bluetooth device using bluetoothctl."""
    print(f"Connecting to {mac_address}...")
    run_command(f"bluetoothctl connect {mac_address}")
    time.sleep(1)  # Wait for connection

def disconnect_bluetooth_device(mac_address):
    """Disconnect a Bluetooth device using bluetoothctl."""
    print(f"Disconnecting from {mac_address}...")
    run_command(f"bluetoothctl disconnect {mac_address}")
    time.sleep(1)  # Allow time for disconnection

def set_default_audio_sink():
    """Set the Bluetooth speaker as the default audio sink in PulseAudio."""
    output = run_command("pactl list sinks short")
    #sinks = [line.split()[1] for line in output.split("\n") if "bluez_sink" in line]
    sinks = [line.split()[1] for line in output.split("\n") if "bluez_output" in line]

    if sinks:
        print(f"Setting default audio sink: {sinks[0]}")
        run_command(f"pactl set-default-sink {sinks[0]}")
    else:
        print("No Bluetooth audio sink found.")

def play_audio(audio_file):
    """Play an audio file using ffplay in the background."""
    print(f"Playing audio file: {audio_file}")
    subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_file])

def switch_audio_to_speaker(speaker_to_connect, speaker_to_disconnect):
    """Switch Bluetooth output to another speaker while audio is playing."""
    #disconnect_bluetooth_device(speaker_to_disconnect)
    connect_bluetooth_device(speaker_to_connect)
    set_default_audio_sink()

if __name__ == "__main__":
    audio_file = "Music/beeping_WAV.wav"  # Replace with your actual audio file path or URL

    # Play on Speaker 1
    connect_bluetooth_device(BT_SPEAKER_1)
    set_default_audio_sink()
    play_audio(audio_file)

    # Wait 3 seconds
    time.sleep(3)

    # Switch to Speaker 2
    switch_audio_to_speaker(BT_SPEAKER_2, BT_SPEAKER_1)

    print("Audio should now be playing from Speaker 2.")
