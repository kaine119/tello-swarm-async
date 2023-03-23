from typing import Dict, List, Tuple
from tello import SwarmStrategy, TelloUnit
from tasks import find_pad


class FollowToEndPad(SwarmStrategy):
    def __init__(self,
                 path_pad_no: int,
                 end_pad_no: int,
                 distance_between_pads: int,
                 flight_level_1: int,
                 flight_level_2: int,
                 speed: int) -> None:
        """
        Instruct drones in a swarm to follow a path of mission pads, landing when
        a particular pad number is seen.
        :param path_pad_no: The number on the mission pads along the path.
        :param end_pad_no: The number of the mission pad that ends the path; the drone will land
        upon seeing this path.
        :param distance_between_pads: How far forward to fly per pad.
        :param altitude: The altitude that the drone flies at.
        :param speed: How fast the drones fly per pad.
        """
        self.path_pad_no = path_pad_no
        self.end_pad_no = end_pad_no
        self.distance_between_pads = distance_between_pads
        self.flight_level_1 = flight_level_1
        self.flight_level_2 = flight_level_2
        self.speed = speed

        self.pad_finder = find_pad.FindPadTask()

    def next_task(self,
                  tello: TelloUnit,
                  last_task_result: str,
                  tellos: List[TelloUnit]) -> Tuple[bool, str | None]:
        index = tellos.index(tello)
        altitude = self.flight_level_1 if index % 2 == 0 else self.flight_level_2
        if tello.detected_marker is None:
            print(
                f"[FollowToEndPadStrategy] [{tello.ip}] Failed to find marker, attempting to recover")
            # If we haven't seen a pad, try to go forward and see if we can detect one.
            return (
                True,
                self.pad_finder.execute(tello, altitude)
            )
        elif tello.detected_marker != self.end_pad_no:
            if tello.marker_yaw is None:
                print(
                    f"[FollowToEndPadStrategy] [{tello.ip}] help, drone detected marker but no yaw???")
                return False, None
            self.tellos_last_search_tasks[tello] = None
            print(
                f"[FollowToEndPadStrategy] [{tello.ip}] Current marker_yaw {tello.marker_yaw}")
            if abs(tello.marker_yaw) >= 10:
                print(
                    f"[FollowToEndPadStrategy] [{tello.ip}] Aligning yaw to path pad; current yaw {tello.marker_yaw}")
                # return (
                #     True,
                #     f'jump 0 0 {altitude} 10 0 m{self.path_pad_no} m{self.path_pad_no}'
                # )
                yaw_command = "cw" if tello.marker_yaw > 0 else "ccw"
                return (
                    True,
                    f'{yaw_command} {abs(tello.marker_yaw)}'
                )
            else:
                return (
                    True,
                    f'go {self.distance_between_pads} 0 {altitude} {self.speed} m{self.path_pad_no}'
                )
        else:
            if tello.marker_xy is None:
                print(
                    f"[FollowToEndPadStrategy] [{tello.ip}] help, drone detected marker but no coordinates???")
                return False, None
            marker_x, marker_y = tello.marker_xy
            if abs(marker_x) <= 10 and abs(marker_y) <= 10:
                print(
                    f"[FollowToEndPadStrategy] [{tello.ip}] Successfully aligned to landing pad; current rel coordinates {tello.marker_xy}")
                return False, None
            else:
                print(
                    f"[FollowToEndPadStrategy] [{tello.ip}] Aligning to landing pad; current rel coordinates {tello.marker_xy}")
                return (
                    True,
                    f'go 0 0 {altitude} {self.speed} m{self.end_pad_no}'
                )
