#!/usr/bin/env python3
"""
Read Murata / NXP Type-2BP UART stream and print only:
    distance  (m)
    azimuth   (°)
    elevation (°)

Baud-rate 3 000 000 Bd is the SR150 default ≥ v04.04.03
Change SERIAL_PORT if your port differs.
"""
import re
import serial

SERIAL_PORT = "/dev/ttyUSB0"      # or /dev/ttyAMA0, /dev/ttyACM0 … depending on rpi version. check port using "mode" in windows terminal after ssh-ing into rpi
BAUD       = 3_000_000

# Pre-compiled regexes (tolerate any spaces around the colon)
re_dist  = re.compile(r"TWR\[\d+\]\.distance\s*:\s*([-\d.]+)")
re_azimu = re.compile(r"TWR\[\d+\]\.aoa_azimuth\s*:\s*([-\d.]+)")
re_elev  = re.compile(r"TWR\[\d+\]\.aoa_elevation\s*:\s*([-\d.]+)")

def main() -> None:
    ser = serial.Serial(SERIAL_PORT, BAUD)
    distance = azimuth = elevation = None

    print("Waiting for data from UART…")
    while True:
        raw = ser.readline().decode(errors="ignore").strip()

        # Uncomment next line once you’re confident it’s working
        # print("RAW >", raw)

        if distance is None:
            m = re_dist.search(raw)
            if m:
                distance = m.group(1)

        if azimuth is None:
            m = re_azimu.search(raw)
            if m:
                azimuth = m.group(1)

        if elevation is None:
            m = re_elev.search(raw)
            if m:
                elevation = m.group(1)

        # Once all three present → print & reset
        if None not in (distance, azimuth, elevation):
            print(f"Distance: {distance} m,  "
                  f"Azimuth: {azimuth}°,  "
                  f"Elevation: {elevation}°")
            distance = azimuth = elevation = None

if __name__ == "__main__":
    main()






