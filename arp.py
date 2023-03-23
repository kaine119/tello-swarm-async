import sys
from datetime import datetime
from scapy.all import srp, Ether, ARP, conf


def arp_scan():
    target_ip = "192.168.50.1/24"
    arp = ARP(pdst=target_ip)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether/arp

    result = srp(packet, timeout=3)[0]

    clients = {}

    for sent, received in result:
        clients[received.hwsrc] = received.psrc
    return clients
