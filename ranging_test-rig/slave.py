#!/usr/bin/env python3
# slave_uart_pub.py — UART→vectors→MQTT (paho v1.x)
import os, re, json, time, math, serial
from datetime import datetime
import paho.mqtt.client as mqtt

DEVICE_ID  = input("Enter device_id for SLAVE: ").strip() or "slave-1"
BROKER_HOST= input("Enter MASTER broker host (default mqtt-broker.local): ").strip() or "mqtt-broker.local"
BROKER_PORT= 1883
TOPIC      = f"house/anchors/{DEVICE_ID}"

SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
BAUD        = int(os.getenv("BAUD", "3000000"))

INCLUDE_RAW, INCLUDE_LOCAL, INCLUDE_GLOBAL = True, True, True
ANCHOR_POSE = {0:(45.0,0.0,0.0), 1:(135.0,0.0,0.0), 2:(-135.0,0.0,0.0), 3:(-45.0,0.0,0.0)}

re_dist  = re.compile(r"TWR\[(\d+)\]\.distance\s*:\s*([-\d.]+)")
re_azimu = re.compile(r"TWR\[(\d+)\]\.aoa_azimuth\s*:\s*([-\d.]+)")
re_elev  = re.compile(r"TWR\[(\d+)\]\.aoa_elevation\s*:\s*([-\d.]+)")

def deg2rad(d): return d * 3.141592653589793 / 180.0
def r_local_from_az_el(r, az, el):
    th, ph = deg2rad(az), deg2rad(el)
    cph, sph, cth, sth = math.cos(ph), math.sin(ph), math.cos(th), math.sin(th)
    return (r*cph*cth, -r*cph*sth, -r*sph)

def rot_zyx(yaw, pitch, roll):
    cy, sy = math.cos(deg2rad(yaw)),   math.sin(deg2rad(yaw))
    cp, sp = math.cos(deg2rad(pitch)), math.sin(deg2rad(pitch))
    cr, sr = math.cos(deg2rad(roll)),  math.sin(deg2rad(roll))
    a00,a01,a02 = cy*cp, -sy*cp, -cy*sp
    a10,a11,a12 = sy*cp,  cy*cp, -sy*sp
    a20,a21,a22 =     sp,      0,     cp
    return ((a00, a01*cr - a02*sr, a01*sr + a02*cr),
            (a10, a11*cr - a12*sr, a11*sr + a12*cr),
            (a20, a21*cr - a22*sr, a21*sr + a22*cr))

def apply_R(R, v): return (R[0][0]*v[0]+R[0][1]*v[1]+R[0][2]*v[2],
                           R[1][0]*v[0]+R[1][1]*v[1]+R[1][2]*v[2],
                           R[2][0]*v[0]+R[2][1]*v[1]+R[2][2]*v[2])

def on_connect(c,u,f,rc): print("Connected" if rc==0 else f"Connect failed rc={rc}")

client = mqtt.Client(client_id=f"uartpub-{DEVICE_ID}")
client.on_connect = on_connect
client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
client.loop_start()

R_anchor = {aid: rot_zyx(*pose) for aid, pose in ANCHOR_POSE.items()}
pending, seq = {}, 0
ser = serial.Serial(SERIAL_PORT, BAUD)
print(f"UART {SERIAL_PORT}@{BAUD}. Publishing to {BROKER_HOST} topic {TOPIC}. Ctrl+C to stop.")
try:
    while True:
        s = ser.readline().decode(errors="ignore").strip()
        m = re_dist.search(s);   m and pending.setdefault(int(m.group(1)),{}).__setitem__("r",  float(m.group(2)))
        m = re_azimu.search(s);  m and pending.setdefault(int(m.group(1)),{}).__setitem__("az", float(m.group(2)))
        m = re_elev .search(s);  m and pending.setdefault(int(m.group(1)),{}).__setitem__("el", float(m.group(2)))

        for aid, st in list(pending.items()):
            if all(k in st for k in ("r","az","el")):
                r, az, el = st["r"], st["az"], st["el"]
                v_local = r_local_from_az_el(r, az, el)
                R = R_anchor.get(aid, ((1,0,0),(0,1,0),(0,0,1)))
                v_global = apply_R(R, v_local)

                sample = {"t_unix_ns": time.time_ns(), "anchor_id": aid}
                if INCLUDE_LOCAL:  sample["vector_local"]  = {"x": v_local[0],  "y": v_local[1],  "z": v_local[2]}
                if INCLUDE_GLOBAL: sample["vector_global"] = {"x": v_global[0], "y": v_global[1], "z": v_global[2]}
                if INCLUDE_RAW:    sample["raw"] = {"distance_m": r, "azimuth_deg": az, "elevation_deg": el}

                payload = {"device_id": DEVICE_ID, "ts": datetime.utcnow().isoformat()+"Z", "seq": seq, "body": sample}
                client.publish(TOPIC, json.dumps(payload), qos=0, retain=False)
                seq += 1
                pending.pop(aid, None)
except KeyboardInterrupt:
    pass
finally:
    client.loop_stop(); client.disconnect(); ser.close()
