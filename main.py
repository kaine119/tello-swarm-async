import asyncio
from strategies import *
from arp import arp_scan, ping_ips

from swarm import SwarmManager

path_pads = [1, 3]
end_pads = [5, 6, 7, 8]
distance = 200
flight_1 = 50
flight_2 = 50
speed = 20


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
