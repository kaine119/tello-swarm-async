from typing import List, Tuple
from tello import SwarmStrategy, TelloUnit


class FollowToEndPad(SwarmStrategy):
    def __init__(self,
                 path_pad_no: int,
                 end_pad_no: int,
                 distance_between_pads: int,
                 base_altitude: int,
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
        self.base_altitude = base_altitude
        self.speed = speed

    def next_task(self,
                  tello: TelloUnit,
                  last_task_result: str,
                  tellos: List[TelloUnit]) -> Tuple[bool, str | None]:
        index = tellos.index(tello)
        altitude = self.base_altitude + index * 15
        if tello.detected_marker != self.end_pad_no:
            return (
                True,
                f'go {self.distance_between_pads} 0 {altitude} {self.speed} m{self.path_pad_no}'
            )
        else:
            return False, None
