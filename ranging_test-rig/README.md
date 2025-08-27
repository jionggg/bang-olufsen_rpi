# Set up RPis


## Master RPi
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
