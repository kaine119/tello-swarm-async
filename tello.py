import asyncio
from asyncio import AbstractEventLoop, Future, transports
from collections import deque
import functools
from typing import Any, Dict, List
import time


class TelloUnit:
    def __init__(self, ip: str, task_list: List[str]) -> None:
        self.ip = ip
        self.task_list = task_list
        self.on_msg_received: Future | None = None
        self.on_tof_received: Future | None = None
        self.started = False
        self.detected_marker: int | None = None
        self.front_tof = 0


class TelloControlProtocol(asyncio.DatagramProtocol):
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
        self.on_tof_received_for = {}

    def send_command(self, command: str, tello: TelloUnit):
        """
        Send a command to a TelloUnit.

        The TelloUnit's `current_future` will be fulfilled when acknowledgement has been
        received from the Tello.
        """

        if self.transport is not None:
            if command == 'EXT tof?':
                self.on_tof_received_for[tello.ip] = tello.on_tof_received
            else:
                self.on_message_received_for[tello.ip] = tello.on_msg_received
            print(f"[TelloControlProtocol] Sending {command} to {tello.ip}")
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
        if data[0:4] == b'tof ':
            self.on_tof_received_for[addr[0]].set_result(data)
        else:
            self.on_message_received_for[addr[0]].set_result(data)

    def error_received(self, exc: Exception) -> None:
        super().error_received(exc)
        print(f"[TelloClientProtocol] Error: {exc}")

    def connection_lost(self, exc: Exception | None) -> None:
        super().connection_lost(exc)
        print("[TelloClientProtocol] Connection closed")
        self.on_conn_lost.set_result(True)


class TelloStatusProtocol(asyncio.DatagramProtocol):
    STATUS_PORT = 8890

    def __init__(self, tellos: List[TelloUnit]) -> None:
        super().__init__()
        self.tello_by_ip = {tello.ip: tello for tello in tellos}

    def connection_made(self, transport: transports.DatagramTransport) -> None:
        super().connection_made(transport)
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str | Any, int]) -> None:
        super().datagram_received(data, addr)
        if addr[0] not in self.tello_by_ip.keys():
            return
        mid = data.decode('utf-8').split(';')[0].split(':')[1]
        self.tello_by_ip[addr[0]].detected_marker = int(mid) if int(mid) > 0 else None

    def connection_lost(self, exc: Exception | None) -> None:
        super().connection_lost(exc)


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

            tello.on_tof_received = self.loop.create_future()
            # A bit annoying to do this, but we can't really await multiple async calls
            # and respond to each call independently.
            tello.on_tof_received.add_done_callback(
                functools.partial(self.tof_received_callback, tello)
            )

    async def start_all_drones(self):
        """
        Sends `command` to all drones, to put them in SDK mode.
        """
        self.control_transport, self.control_protocol = await self.loop.create_datagram_endpoint(
            lambda: TelloControlProtocol(self.on_con_lost),
            local_addr=('0.0.0.0', 42345)
        )

        self.status_transport, self.status_protocol = await self.loop.create_datagram_endpoint(
            lambda: TelloStatusProtocol(self.tellos),
            local_addr=('0.0.0.0', TelloStatusProtocol.STATUS_PORT)
        )

        for tello in self.tellos:
            self.control_protocol.send_command("command", tello)
            self.control_protocol.send_command("EXT tof?", tello)

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
        print(f"[SwarmManager] Received {data} from {tello.ip}")
        if data in [b'ok', b'led ok', b'mled ok']:
            print(f"[SwarmManager] Received ok from drone {tello.ip}")
        if tello.started:
            tello.task_list.pop(0)
        else:
            tello.started = True
        print(f"[SwarmManager] Drone {tello.ip} detects mission pad {tello.detected_marker}")
        if len(tello.task_list) != 0:
            next_task = tello.task_list[0]
            print(f"[SwarmManager] Sending command '{next_task}' to drone {tello.ip}")
            tello.on_msg_received = self.loop.create_future()
            tello.on_msg_received.add_done_callback(
                functools.partial(self.msg_received_callback, tello)
            )
            self.control_protocol.send_command(next_task, tello)
        else:
            # We're done for this drone.
            print(f"[SwarmManager] Tasking complete for drone {tello.ip}")

            # If we're done for all drones, close the socket.
            if (all(len(tello.task_list) == 0 for tello in self.tellos)):
                self.control_transport.close()

    def tof_received_callback(self, tello: TelloUnit, received_future: Future):
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
        tello.front_tof = int(data.decode('utf-8')[4:])
        if tello.front_tof < 500:
            self.control_protocol.send_command('land', tello)
            if tello.on_msg_received is not None:
                tello.on_msg_received.remove_done_callback(functools.partial(self.msg_received_callback, tello))
        else:
            tello.on_tof_received = self.loop.create_future()
            tello.on_tof_received.add_done_callback(
                functools.partial(self.tof_received_callback, tello)
            )
            time.sleep(0.5)
            self.control_protocol.send_command('EXT tof?', tello)


async def main():
    loop = asyncio.get_running_loop()

    tasks = {
        "192.168.50.51": ['takeoff', 'EXT led 0 255 0', "go 150 0 50 30 m1","go 150 0 50 30 m1" 'land'],
        # "192.168.50.52": ['takeoff', 'EXT led 0 255 0', "forward 250", 'land']
    }

    manager = SwarmManager(loop, tasks)
    await manager.start_all_drones()

    await manager.on_con_lost


if __name__ == "__main__":
    asyncio.run(main())
