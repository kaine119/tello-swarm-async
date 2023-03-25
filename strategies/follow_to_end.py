from typing import Dict, List, Tuple
from tello import TelloUnit
from tasks import *
from swarm import *


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
        self.pad_align = align_pad.AlignPadTask(speed, distance_between_pads, path_pad_no, end_pad_no)

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
            return self.pad_finder.execute(tello, altitude)
        elif tello.detected_marker != self.end_pad_no:
            if tello.marker_yaw is None:
                print(
                    f"[FollowToEndPadStrategy] [{tello.ip}] help, drone detected marker but no yaw???")
                return False, None
            self.pad_finder.reset_tasks(tello)
            print(
                f"[FollowToEndPadStrategy] [{tello.ip}] Current marker_yaw {tello.marker_yaw}")
            return self.pad_align.align_pad(tello, altitude)
        else:
            if tello.marker_xy is None:
                print(
                    f"[FollowToEndPadStrategy] [{tello.ip}] help, drone detected marker but no coordinates???")
                return False, None
            return self.pad_align.align_end_pad(tello, altitude)

    def on_tello_updated(self, tello: TelloUnit) -> bool:
        print(tello.detected_marker)
        if tello.detected_marker == self.end_pad_no:
            return True
        return False
