import asyncio
from strategies import *
from arp import arp_scan

from swarm import SwarmManager

# Last 3 bytes of the MAC address of each Tello.
# Identified by the SSID printed on the
# back of the head unit (RMTT-______)
# Separate every 2 characters with a colon.
macs = [
    "f2:43:0e"
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


path_pads = [1, 3]
end_pads = [5, 6, 7, 8]
distance = 100
flight_1 = 50
flight_2 = 50
speed = 50


async def main():
    loop = asyncio.get_running_loop()
    strategy = follow_to_end.FollowToEndPad(
        path_pads, end_pads, distance, flight_1, flight_2, speed)
    ips = ping_ips()

    manager = SwarmManager(loop, ips, strategy)
    await manager.start_all_drones()

    await manager.on_con_lost


if __name__ == "__main__":
    asyncio.run(main())
