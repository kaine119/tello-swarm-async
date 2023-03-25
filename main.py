import asyncio
from strategies import *
from arp import arp_scan

from swarm import SwarmManager

# Last 3 bytes of the MAC address of each Tello.
# Identified by the SSID printed on the
# back of the head unit (RMTT-______)
# Separate every 2 characters with a colon.
macs = [
    "10:b4:3A"
]


def ping_ips():
    clients = arp_scan()
    ips = []
    print(clients)
    for mac in macs:
        mac = mac.lower()
        if clients.get(mac) is None:
            print("MAC address not found:", mac)
            ips.append("192.168.51.1")
        else:
            ips.append(clients[mac])
    print(ips)
    return ips


async def main():
    loop = asyncio.get_running_loop()
    strategy = follow_to_end.FollowToEndPad(1, 5, 400, 50, 150, 50)
    ips = ping_ips()

    manager = SwarmManager(loop, ips, strategy)
    await manager.start_all_drones()

    await manager.on_con_lost


if __name__ == "__main__":
    asyncio.run(main())
