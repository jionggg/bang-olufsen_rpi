# MQTT-Controlled Synchronized Audio Panning

This project creates a simple but powerful **synchronized audio panning system** across two Raspberry Pis using **MQTT**.  
A laptop hosts the broker and acts as the controller (via keyboard), while each Pi acts as a client driving a speaker.  

Use case: synchronized **left-right audio panning** or "follow-me audio" demos.

---

## 🗂 Project Structure

- `broker_and_keyboard_publisher.py`  
  Laptop script that:
  - Starts a local Mosquitto broker (if installed).
  - Listens for keyboard input (`Enter`, `a`, `d`, `q`).
  - Publishes JSON commands to MQTT with a scheduled `execute_at` timestamp (global clock + 0.5s).

- `rpi_listener.py`  
  Raspberry Pi script that:
  - Subscribes to the same MQTT topic.
  - At the scheduled `execute_at` time, executes the command by adjusting volume or starting playback.
  - Plays music locally on each Pi through the 3.5mm jack.

---

## ⚙️ Requirements

### On the Laptop (Controller)
- **Mosquitto broker** (installed system-wide and available in PATH).
- Python 3.x with dependencies:
  ```bash
  pip install paho-mqtt pynput
