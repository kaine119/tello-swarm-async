import asyncio
from strategies import *

from tello import SwarmManager


async def main():
    loop = asyncio.get_running_loop()
    strategy = follow_to_end.FollowToEndPad(1, 5, 380, 50, 150, 50)
    ips = [
        "192.168.50.56",  # 109b7a
        "192.168.50.58",  # 10c428
        "192.168.50.61",  # 10b17c
        "192.168.50.57",  # f23b1a
        "192.168.50.55"  # 9aecdc
    ]

    manager = SwarmManager(loop, ips, strategy)
    await manager.start_all_drones()

    await manager.on_con_lost


if __name__ == "__main__":
    asyncio.run(main())
