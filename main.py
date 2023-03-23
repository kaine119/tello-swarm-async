import asyncio
from strategies import *
from arp import arp_scan

from swarm import SwarmManager

macs = [
    "74:7A:90:F2:3B:1A",
    "18:48:CA:9A:EC:C6",
    "E8:4F:25:10:9B:7A",
    "E8:4F:25:10:C4:28",
    "18:48:CA:9A:EC:DC",
    "58:D5:0A:D2:71:04",
    "E8:4F:25:10:B1:7C",
    "E8:4F:25:10:9B:EC",
    "E8:4F:25:10:9B:B4",
    "74:7A:90:9B:6F:6C",
]


def ping_ips():
    clients = arp_scan()
    ips = []
    for mac in macs:
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
