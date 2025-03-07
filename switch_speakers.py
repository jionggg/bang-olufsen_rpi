import subprocess
import time

# Define MAC addresses of your Bluetooth speakers
BT_SPEAKER_2 = "04:FE:A1:DB:7D:01"  # MAC of Beoplay P2
#BT_SPEAKER_1 = "172.31.62.25"  #MAC of my msi laptop
#BT_SPEAKER_1 = "68:59:32:28:1D:0C" # MAC of Marshall Middleton
BT_SPEAKER_1 = "20:18:5B:51:55:B7"  # MAC of NUSC JBL Flip 6


def run_command(command):
    """Run a shell command and return output."""
    process = subprocess.run(command, shell=True, capture_output=True, text=True)
    return process.stdout.strip()

def connect_bluetooth_device(mac_address):
    """Connect to a Bluetooth device using bluetoothctl."""
    print(f"Connecting to {mac_address}...")
    run_command(f"bluetoothctl connect {mac_address}")
    #time.sleep(1)  # Wait for connection

def set_default_audio_sink(sink_name):      #changed from v2
    """Set the Bluetooth speaker as the default audio sink and move audio streams to it."""
    print(f"Switching audio to: {sink_name}")
    run_command(f"pactl set-default-sink {sink_name}")
    
    # Move all currently playing audio to the new sink
    output = run_command("pactl list sink-inputs short")  # ✅ Corrected pactl list sinks short
    sink_inputs = [line.split()[0] for line in output.split("\n") if line]

    for sink_input in sink_inputs:
        print(f"Moving audio stream {sink_input} to {sink_name}")
        run_command(f"pactl move-sink-input {sink_input} {sink_name}")

def play_audio(audio_file):
    """Play an audio file using ffplay in the background."""
    print(f"Playing audio file: {audio_file}")
    subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_file])

def switch_audio_to_speaker(speaker_mac):       #changed from v2
    """Switch Bluetooth output to another speaker while audio is playing."""
    connect_bluetooth_device(speaker_mac)  # Ensure the speaker is connected

    # Find the correct sink
    sinks = run_command("pactl list sinks short")
    matching_sinks = [line.split()[1] for line in sinks.split("\n") if speaker_mac.replace(":", "_") in line]

    if matching_sinks:
        set_default_audio_sink(matching_sinks[0])
    else:
        print(f"Error: No audio sink found for {speaker_mac}")

if __name__ == "__main__":
    audio_file = "Music/beeping_WAV.wav"  # Replace with your actual audio file path or URL

    # Play on Speaker 1
    connect_bluetooth_device(BT_SPEAKER_1)
    
    sinks = run_command("pactl list sinks short")
    matching_sinks = [line.split()[1] for line in sinks.split("\n") if "bluez_output" in line]
    if matching_sinks:
        set_default_audio_sink(matching_sinks[0])  # Pass the correct sink name
    else:
        print("Error: No Bluetooth audio sinks found.")
    
    play_audio(audio_file)

    # Wait 3 seconds
    time.sleep(3)

    # Switch to Speaker 2
    switch_audio_to_speaker(BT_SPEAKER_2)

    print("Audio should now be playing from Speaker 2.")
