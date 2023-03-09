import asyncio
from strategies import FollowToEndPad

from tello import SwarmManager


async def main():
    loop = asyncio.get_running_loop()
    strategy = FollowToEndPad(8, 4, 150, 50, 50)
    ips = [
        "192.168.50.50",
        "192.168.50.54"
    ]

    manager = SwarmManager(loop, ips, strategy)
    await manager.start_all_drones()

    await manager.on_con_lost


if __name__ == "__main__":
    asyncio.run(main())
