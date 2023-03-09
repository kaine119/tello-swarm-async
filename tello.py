import asyncio
from asyncio import AbstractEventLoop, Future, transports
from collections import deque
import functools
from typing import Any, Dict, List


class TelloUnit:
    def __init__(self, ip: str, task_list: List[str]) -> None:
        self.ip = ip
        self.task_list = task_list
        self.on_msg_received: Future | None = None
        self.started = False


class TelloClientProtocol(asyncio.DatagramProtocol):
    CONTROL_PORT = 8889

    def __init__(self, on_conn_lost: Future):
        """
        Control protocol for multiple Tellos. It asynchronously sends UDP packets to each
        unit, waiting for each unit to reply with a `b"ok"`.

        :param on_conn_lost: A `Future` that gets fulfilled if the connection is closed.
        """
        self.transport = None
        self.on_conn_lost = on_conn_lost

        # An internal dictionary mapping IP addresses to the `on_msg_received` callbacks for each
        # TelloUnit sent here.
        self.on_message_received_for = {}

    def send_command(self, command: str, tello: TelloUnit):
        """
        Send a command to a TelloUnit.

        The TelloUnit's `current_future` will be fulfilled when acknowledgement has been
        received from the Tello.
        """

        if self.transport is not None:
            self.on_message_received_for[tello.ip] = tello.on_msg_received
            self.transport.sendto(command.encode('utf-8'), (tello.ip, self.CONTROL_PORT))
        else:
            raise RuntimeError("UDP transport hasn't been initialized yet")

    def connection_made(self, transport: transports.DatagramTransport) -> None:
        super().connection_made(transport)
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str | Any, int]) -> None:
        super().datagram_received(data, addr)

        # Lookup the future for the tello that sent this packet,
        # then fulfil the future.
        self.on_message_received_for[addr[0]].set_result(data)

    def error_received(self, exc: Exception) -> None:
        super().error_received(exc)
        print(f"[TelloClientProtocol] Error: {exc}")

    def connection_lost(self, exc: Exception | None) -> None:
        super().connection_lost(exc)
        print("[TelloClientProtocol] Connection closed")
        self.on_conn_lost.set_result(True)


class SwarmManager:
    def __init__(self, loop: AbstractEventLoop, tasks: Dict[str, List[str]]) -> None:
        """
        Manages multiple TelloUnits. It keeps track of multiple tasking lists, and sends commands
        to each drone as the drone completes them.

        :param loop: The event loop to run under.
        :param tasks: A dict mapping Tello IP addresses to the list of commands they are to complete.
        """
        self.loop = loop

        self.tellos = [TelloUnit(ip, task_list) for ip, task_list in tasks.items()]

        self.on_con_lost = loop.create_future()

        # Create each TelloUnit's `on_msg_received` future, and register a handler to it.
        for tello in self.tellos:
            tello.on_msg_received = self.loop.create_future()
            # A bit annoying to do this, but we can't really await multiple async calls
            # and respond to each call independently.
            tello.on_msg_received.add_done_callback(
                functools.partial(self.msg_received_callback, tello)
            )

    async def start_all_drones(self):
        """
        Sends `command` to all drones, to put them in SDK mode.
        """
        self.transport, self.protocol = await self.loop.create_datagram_endpoint(
            lambda: TelloClientProtocol(self.on_con_lost),
            local_addr=('0.0.0.0', 42345)
        )
        for tello in self.tellos:
            if tello.on_msg_received is not None:
                self.protocol.send_command("command", tello)

    def msg_received_callback(self, tello: TelloUnit, received_future: Future):
        """
        Handler for when we receive an acknowledgement packet from the Tello unit.

        Checks if the tasking for that particular unit is done; if not, it will send the next
        command out. If all units managed by the `SwarmHandler` have completed their tasking, the
        transport will be closed, fulfilling `self.on_con_lost`.

        To be used as a partial function call when registering callbacks:

        ```
        future.add_done_callback(functools.partial(self.handle_ack, tello))
        ```

        :param tello: The TelloUnit this handler was registered to.
        :param received_future: To be filled in by `add_done_callback`.
        """
        data = received_future.result()
        if data == b'ok':
            print(f"[SwarmManager] Received ok from drone {tello.ip}")
            if tello.started:
                tello.task_list.pop(0)
            else:
                tello.started = True
            if len(tello.task_list) != 0:
                next_task = tello.task_list[0]
                print(f"[SwarmManager] Sending command '{next_task}' to drone {tello.ip}")
                tello.on_msg_received = self.loop.create_future()
                tello.on_msg_received.add_done_callback(
                    functools.partial(self.msg_received_callback, tello)
                )
                self.protocol.send_command(next_task, tello)
            else:
                # We're done for this drone.
                print(f"[SwarmManager] Tasking complete for drone {tello.ip}")

                # If we're done for all drones, close the socket.
                if (all(len(tello.task_list) == 0 for tello in self.tellos)):
                    self.transport.close()


async def main():
    loop = asyncio.get_running_loop()

    tasks = {
        "192.168.50.51": ['takeoff', 'EXT led 255 0 0', 'land'],
        "192.168.50.52": ['takeoff', 'EXT led 0 255 0', 'land']
    }

    manager = SwarmManager(loop, tasks)
    await manager.start_all_drones()

    await manager.on_con_lost


if __name__ == "__main__":
    asyncio.run(main())
