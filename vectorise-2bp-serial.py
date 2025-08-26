#!/usr/bin/env python3
"""
UWB → Vector JSON logger (RPi)

Reads Dist/m, Azi/deg, Elev/deg from 2BP UART,
converts to Cartesian vector (x,y,z), and writes rolling JSON files.

Coordinate convention:
- Azimuth θ: angle in XY-plane from +X toward +Y (CCW).
- Elevation φ: angle from horizon (XY-plane) upward (-Z).   

say:
cφ = cos(el_rad)
sφ = sin(el_rad)
cθ = cos(az_rad)
sθ = sin(az_rad)

x_local =  r * cφ * cθ
y_local = -r * cφ * sθ     # minus because +az is “to the right”
z_local = -r * sφ          # minus because +el is “down”      

Tune FILE_MAX_SECONDS / FILE_MAX_SAMPLES as you like.

Dependencies: pyserial
  sudo apt-get install -y python3-serial
"""

import os, re, json, time, math, serial
from datetime import datetime

# ====== CONFIG ======
SERIAL_PORT = "/dev/ttyUSB0"
BAUD        = 3_000_000

FILE_MAX_SECONDS = 1.0
FILE_MAX_SAMPLES = 200
OUT_DIR          = "./uwb_json"

INCLUDE_RAW   = True
INCLUDE_LOCAL = True  # keep local vector for debugging/PGO
INCLUDE_GLOBAL= True

# Per-anchor orientation (degrees). Fill these with your real headings.
# yaw: CCW about +Z from global +X; pitch: about +Y; roll: about +X.
ANCHOR_POSE = {
    # id : (yaw_deg, pitch_deg, roll_deg)
    0: (  45.0, 0.0, 0.0),   # example: facing 45° toward room center
    1: ( 135.0, 0.0, 0.0),
    2: (-135.0, 0.0, 0.0),
    3: ( -45.0, 0.0, 0.0),
    # add more as needed
}

# ====== REGEX ======
re_dist  = re.compile(r"TWR\[(\d+)\]\.distance\s*:\s*([-\d.]+)")
re_azimu = re.compile(r"TWR\[(\d+)\]\.aoa_azimuth\s*:\s*([-\d.]+)")
re_elev  = re.compile(r"TWR\[(\d+)\]\.aoa_elevation\s*:\s*([-\d.]+)")

def deg2rad(d): return d * math.pi / 180.0

def r_local_from_az_el(dist_m: float, az_deg: float, el_deg: float):
    """
    Your convention:
      +az = right, -az = left; 0 = forward (board normal)
      +el = down,  -el = up;   0 = horizontal
    Local axes: x=forward, y=left, z=up
    """
    th = deg2rad(az_deg)
    ph = deg2rad(el_deg)
    cph, sph = math.cos(ph), math.sin(ph)
    cth, sth = math.cos(th), math.sin(th)

    x = dist_m * cph * cth
    y = -dist_m * cph * sth   # minus: +az is to the RIGHT
    z = -dist_m * sph         # minus: +el is DOWN
    return (x, y, z)

def rot_zyx(yaw_deg: float, pitch_deg: float, roll_deg: float):
    """R = Rz(yaw) @ Ry(pitch) @ Rx(roll), all degrees, right-handed, + angles are CCW."""
    cy, sy = math.cos(deg2rad(yaw_deg)),   math.sin(deg2rad(yaw_deg))
    cp, sp = math.cos(deg2rad(pitch_deg)), math.sin(deg2rad(pitch_deg))
    cr, sr = math.cos(deg2rad(roll_deg)),  math.sin(deg2rad(roll_deg))
    # Rz
    r00 = cy;  r01 = -sy; r02 = 0.0
    r10 = sy;  r11 =  cy; r12 = 0.0
    r20 = 0.0; r21 = 0.0; r22 = 1.0
    # Ry
    RzRy = (
        r00*cp + r02*sp,     r01*cp + r02*0,     -r00*sp + r02*cp,
        r10*cp + r12*sp,     r11*cp + r12*0,     -r10*sp + r12*cp,
        r20*cp + r22*sp,     r21*cp + r22*0,     -r20*sp + r22*cp,
    )
    a00,a01,a02,a10,a11,a12,a20,a21,a22 = RzRy
    # Rx
    b00 = a00
    b01 = a01*cr - a02*sr
    b02 = a01*sr + a02*cr
    b10 = a10
    b11 = a11*cr - a12*sr
    b12 = a11*sr + a12*cr
    b20 = a20
    b21 = a21*cr - a22*sr
    b22 = a21*sr + a22*cr
    return ((b00,b01,b02),(b10,b11,b12),(b20,b21,b22))

def apply_R(R, v):
    return (
        R[0][0]*v[0] + R[0][1]*v[1] + R[0][2]*v[2],
        R[1][0]*v[0] + R[1][1]*v[1] + R[1][2]*v[2],
        R[2][0]*v[0] + R[2][1]*v[1] + R[2][2]*v[2],
    )

def new_filename():
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    return os.path.join(OUT_DIR, f"uwb_vectors_{ts}Z.json")

def ensure_dir(p): os.makedirs(p, exist_ok=True)

def main():
    ensure_dir(OUT_DIR)
    ser = serial.Serial(SERIAL_PORT, BAUD)
    print("UART open. Converting (r,az,el) ➜ vectors (local/global)…")

    # per-anchor partials
    pending = {}  # id -> {"r":..., "az":..., "el":...}

    # precompute rotation matrices
    R_anchor = {aid: rot_zyx(*pose) for aid, pose in ANCHOR_POSE.items()}

    buf = []
    file_start = time.time()
    fname = new_filename()

    def flush():
        nonlocal buf, file_start, fname
        if not buf: return
        tmp = fname + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(buf, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, fname)
        print(f"Wrote {len(buf)} samples → {fname}")
        buf = []
        file_start = time.time()
        fname = new_filename()

    try:
        while True:
            s = ser.readline().decode(errors="ignore").strip()

            m = re_dist.search(s)
            if m:
                aid, val = int(m.group(1)), float(m.group(2))
                st = pending.setdefault(aid, {})
                st["r"] = val

            m = re_azimu.search(s)
            if m:
                aid, val = int(m.group(1)), float(m.group(2))
                st = pending.setdefault(aid, {})
                st["az"] = val

            m = re_elev.search(s)
            if m:
                aid, val = int(m.group(1)), float(m.group(2))
                st = pending.setdefault(aid, {})
                st["el"] = val

            # complete triple?
            to_clear = []
            for aid, st in pending.items():
                if all(k in st for k in ("r","az","el")):
                    r, az, el = st["r"], st["az"], st["el"]

                    v_local = r_local_from_az_el(r, az, el)

                    # rotate to global if pose known, else pass-through
                    R = R_anchor.get(aid, ((1,0,0),(0,1,0),(0,0,1)))
                    v_global = apply_R(R, v_local)

                    sample = {
                        "t_unix_ns": time.time_ns(),
                        "anchor_id": aid,
                    }
                    if INCLUDE_LOCAL:
                        sample["vector_local"]  = {"x": v_local[0],  "y": v_local[1],  "z": v_local[2]}
                    if INCLUDE_GLOBAL:
                        sample["vector_global"] = {"x": v_global[0], "y": v_global[1], "z": v_global[2]}
                    if INCLUDE_RAW:
                        sample["raw"] = {
                            "distance_m": r,
                            "azimuth_deg": az,
                            "elevation_deg": el,
                        }
                    buf.append(sample)
                    to_clear.append(aid)

            for aid in to_clear:
                pending.pop(aid, None)

            if (time.time() - file_start) >= FILE_MAX_SECONDS or len(buf) >= FILE_MAX_SAMPLES:
                flush()

    except KeyboardInterrupt:
        print("Stopping…")
    finally:
        try: flush()
        except Exception as e: print("Flush error:", e)
        ser.close()

if __name__ == "__main__":
    main()
