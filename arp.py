import sys
from datetime import datetime
from scapy.all import srp, Ether, ARP, conf

# Last 3 bytes of the MAC address of each Tello.
# Identified by the SSID printed on the
# back of the head unit (RMTT-______)
# Separate every 2 characters with a colon.
macs = [
    # "10:9b:b4",
    # "f2:48:dc",
    "d3:91:ca",
    # "9a:ec:c6",
    "33:14:9c",
    "d2:71:04",
    "9b:6f:6c",
    # "9a:ec:dc",
    # "10:b1:7c",
    # "10:ac:0a",
    "33:21:26",
    # "33:14:9a",
    # "f2:3b:1a",
    # "33:09:aa",
    # "10:a9:9c",
]


def ping_ips():
    clients = arp_scan()
    ips = []
    num = 0
    print(clients)
    for mac in macs:
        mac = mac.lower()
        if clients.get(mac) is None:
            num += 1
            print("MAC address not found:", mac)
            ips.append("192.168.51.1")
        else:
            ips.append(clients[mac])
    print(f"{num} drones not found")
    return ips


def arp_scan():
    target_ip = "192.168.50.1/24"
    arp = ARP(pdst=target_ip)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether/arp

    result = srp(packet, timeout=3)[0]

    clients = {}

    for sent, received in result:
        clients[received.hwsrc[-8:].lower()] = received.psrc
    return clients


if __name__ == "__main__":
    ips = ping_ips()
    print(ips)
