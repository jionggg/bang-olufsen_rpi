import subprocess
import time

# Define MAC addresses of your Bluetooth speakers
BT_SPEAKER_1 = "04:FE:A1:DB:7D:01"  # MAC of Beoplay P2
BT_SPEAKER_2 = "20:18:5B:51:55:B7"  # MAC of NUSC JBL Flip 6


def run_command(command):
    """Run a shell command and return output."""
    process = subprocess.run(command, shell=True, capture_output=True, text=True)
    return process.stdout.strip()

def connect_bluetooth_device(mac_address):
    """Connect to a Bluetooth device using bluetoothctl."""
    print(f"Connecting to {mac_address}...")
    run_command(f"bluetoothctl connect {mac_address}")
    time.sleep(3)  # Wait for connection

def disconnect_bluetooth_device(mac_address):
    """Disconnect a Bluetooth device using bluetoothctl."""
    print(f"Disconnecting from {mac_address}...")
    run_command(f"bluetoothctl disconnect {mac_address}")
    time.sleep(2)  # Allow time for disconnection

def set_default_audio_sink():
    """Set the Bluetooth speaker as the default audio sink in PulseAudio."""
    output = run_command("pactl list sinks short")
    sinks = [line.split()[1] for line in output.split("\n") if "bluez_sink" in line]
    
    if sinks:
        print(f"Setting default audio sink: {sinks[0]}")
        run_command(f"pactl set-default-sink {sinks[0]}")
    else:
        print("No Bluetooth audio sink found.")

def play_audio(file_path):
    """Play an audio file using aplay or ffplay."""
    print(f"Playing audio file: {file_path}")
    run_command(f"aplay {file_path}")  # For .wav files
    # Use ffplay for other formats: run_command(f"ffplay -nodisp -autoexit {file_path}")

def switch_speaker(speaker_to_connect, speaker_to_disconnect, audio_file):
    """Switch between speakers and play audio."""
    disconnect_bluetooth_device(speaker_to_disconnect)
    connect_bluetooth_device(speaker_to_connect)
    set_default_audio_sink()
    play_audio(audio_file)

if __name__ == "__main__":
    audio_file = "Music/beeping_WAV.wav"  # Replace with your actual audio file path

    while True:
        choice = input("Select speaker (1 or 2, q to quit): ").strip()
        if choice == "1":
            switch_speaker(BT_SPEAKER_1, BT_SPEAKER_2, audio_file)
        elif choice == "2":
            switch_speaker(BT_SPEAKER_2, BT_SPEAKER_1, audio_file)
        elif choice.lower() == "q":
            break
        else:
            print("Invalid choice. Please enter 1, 2, or q.")
