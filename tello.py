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
        mid = data.decode('utf-8').split(';')[0].split(':')[1]
        self.tello_by_ip[addr[0]].detected_marker = int(mid) if int(mid) > 0 else None

    def error_received(self, exc: Exception) -> None:
        print(exc)
        return super().error_received(exc)

    def connection_lost(self, exc: Exception | None) -> None:
        super().connection_lost(exc)


class SwarmStrategy(object):
    """
    Provides the next step to be taken by any drone in the swarm.
    Override `next_task` to provide behaviour for the next step.
    """

    def next_task(self,
                  tello: TelloUnit,
                  last_task_result: str,
                  tellos: List[TelloUnit]) -> Tuple[bool, str | None]:
        """
        Returns whether there is a next task to take, and if so,
        the next step taken by the drone. This method needs to be
        implemented.

        If there is no next task to do, i.e. the bool returned is False,
        the drone will land in place.

        Will be called after the drone sends an acknowledgement packet to us.
        """
        raise NotImplementedError


class SwarmManager:
    def __init__(self,
                 loop: AbstractEventLoop,
                 tello_ips: List[str],
                 strategy: SwarmStrategy) -> None:
        """
        Manages multiple TelloUnits. It keeps track of multiple tasking lists, and sends commands
        to each drone as the drone completes them.

        :param loop: The event loop to run under.
        :param tasks: A dict mapping Tello IP addresses to the list of commands they are to complete.
        """
        self.loop = loop

        self.tellos = [TelloUnit(ip) for ip in tello_ips]

        self.on_con_lost = loop.create_future()

        self.strategy = strategy

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
        if b'error' in data:
            print(f"[SwarmManager] Received error from drone {tello.ip}")
            should_continue, next_task = False, None
            # just stop doing anything with this one
            tello.finished = True
        elif b'ok' in data:
            print(f"[SwarmManager] Received ok from drone {tello.ip}")

            print(f"[SwarmManager] Drone {tello.ip} detects mission pad {tello.detected_marker}")

            # Get the next task to perform from the strategy.
            should_continue, next_task = self.strategy.next_task(tello, data, self.tellos)

            if not tello.started:
                tello.started = True
                tello.on_msg_received = self.loop.create_future()
                tello.on_msg_received.add_done_callback(
                    functools.partial(self.msg_received_callback, tello)
                )
                self.control_protocol.send_command('takeoff', tello)

            elif not tello.labelled:
                tello.labelled = True
                tello.on_msg_received = self.loop.create_future()
                tello.on_msg_received.add_done_callback(
                    functools.partial(self.msg_received_callback, tello)
                )
                label = chr(97 + self.tellos.index(tello))
                self.control_protocol.send_command(f'EXT mled s r {label}', tello)

            elif should_continue and not tello.finished:
                if next_task is None:
                    raise RuntimeError("No action was provided despite continuing")
                print(f"[SwarmManager] Sending command '{next_task}' to drone {tello.ip}")
                tello.on_msg_received = self.loop.create_future()
                tello.on_msg_received.add_done_callback(
                    functools.partial(self.msg_received_callback, tello)
                )
                self.control_protocol.send_command(next_task, tello)
            else:
                # We're done for this drone.
                print(f"[SwarmManager] Tasking complete for drone {tello.ip}, landing")
                tello.on_msg_received = self.loop.create_future()
                tello.on_msg_received.add_done_callback(
                    functools.partial(self.msg_received_callback, tello)
                )
                self.control_protocol.send_command('land', tello)
                tello.finished = True

                # If we're done for all drones, close the socket.
                if (all(tello.finished for tello in self.tellos)):
                    self.control_transport.close()