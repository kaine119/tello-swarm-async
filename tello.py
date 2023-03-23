import asyncio
from asyncio import AbstractEventLoop, Future, transports
from collections import deque
import functools
from typing import Any, Dict, List, Tuple


class TelloUnit:
    def __init__(self, ip: str) -> None:
        self.ip = ip
        self.on_msg_received: Future | None = None
        self.started = False
        self.labelled = False
        self.finished = False
        self.detected_marker: int | None = None
        self.marker_xy: Tuple[int, int] | None = None
        self.marker_yaw: int | None = None
        self.height: int = 0


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

    def send_command(self, command: str, tello: TelloUnit):
        """
        Send a command to a TelloUnit.

        The TelloUnit's `current_future` will be fulfilled when acknowledgement has been
        received from the Tello.
        """

        if self.transport is not None:
            self.on_message_received_for[tello.ip] = tello.on_msg_received
            print(f"[TelloControlProtocol] Sending {command} to {tello.ip}")
            self.transport.sendto(command.encode(
                'utf-8'), (tello.ip, self.CONTROL_PORT))
        else:
            raise RuntimeError("UDP transport hasn't been initialized yet")

    def connection_made(self, transport: transports.DatagramTransport) -> None:
        super().connection_made(transport)
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str | Any, int]) -> None:
        super().datagram_received(data, addr)

        # Lookup the future for the tello that sent this packet,
        # then fulfil the future.
        if not self.on_message_received_for[addr[0]].done():
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
        data_array = data.decode('utf-8').split(';')
        _, mid = data_array[0].split(':')
        _, x = data_array[1].split(':')
        _, y = data_array[2].split(':')
        _, z = data_array[3].split(':')
        _, mpry = data_array[4].split(':')
        _, height = data_array[14].split(':')

        x = int(x)
        y = int(y)
        z = int(z)

        _, marker_yaw, _ = (int(x) for x in mpry.split(','))

        tello_to_update = self.tello_by_ip[addr[0]]
        tello_to_update.detected_marker = int(mid) if int(mid) > 0 else None
        tello_to_update.marker_xy = (x, y) if int(mid) > 0 else None
        tello_to_update.marker_yaw = marker_yaw if int(mid) > 0 else None
        tello_to_update.height = int(height)

    def error_received(self, exc: Exception) -> None:
        print(exc)
        return super().error_received(exc)

    def connection_lost(self, exc: Exception | None) -> None:
        super().connection_lost(exc)
