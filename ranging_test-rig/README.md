# Set up
```
[Master RPi: Mosquitto broker] ──+
  └─ runs master.py → publishes to house/anchors/<MASTER_ID>
[Slave RPis] ──────────────────────┤
  └─ runs slave.py  → publishes to house/anchors/<SLAVE_ID>
[PC/Laptop] ──────────────────────┘
  └─ runs laptop_subscriber.py → subscribes to house/anchors/# and saves JSON
```


# Set up RPis


## Master RPi   // right now it is RPi3B+
### Install broker
```
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
```
### Set friendly hostname and enable mDNS
```
sudo hostnamectl set-hostname mqtt-broker
sudo sed -i 's/^127\.0\.1\.1.*/127.0.1.1 mqtt-broker/' /etc/hosts
sudo apt install -y avahi-daemon avahi-utils libnss-mdns
sudo systemctl enable --now avahi-daemon
sudo systemctl enable --now mosquitto
sudo reboot
```

## On all RPis
```
pip3 install paho-mqtt
```
or 
```
sudo apt install -y python3-paho-mqtt
```

_check paho installation (optional):_
```
python3 -c "import paho.mqtt.client as mqtt; print('paho-mqtt OK')"
```


# How to run

On master:
```
python3 master.py
```
On slave:
```
python3 slave.py
# when prompted, just press Enter to use mqtt-broker.local
```
On laptop:
```
python3 laptop_subscriber.py
# press Enter to use mqtt-broker.local
```


Master → “Enter device_id for MASTER?”
Any unique, no-spaces name for that RPi. Examples: master-1, anchor-master, rpi-hub.
This makes the topic house/anchors/<your_id>, e.g. house/anchors/master-1.

Slave → “Enter device_id for SLAVE?”
Same idea—unique per device. Examples: anchor-01, anchor-livingroom, anchor-kitchen-2.

Slave → “Enter MASTER broker IP?”
If you set the hostname earlier, enter mqtt-broker.local (or just press Enter if your prompt default is that).
