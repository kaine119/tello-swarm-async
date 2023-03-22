from typing import Dict, List, Tuple
from tello import SwarmStrategy, TelloUnit


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

        self.tellos_last_search_tasks: Dict[TelloUnit, int] = {}
        """
        The last search task that each TelloUnit seen has performed.
        The overall grid search pattern is:
        0: Go left
        1: Go forward
        2: Go right
        3: Go right
        4: Go forward
        5: Go left
        """

    def next_task(self,
                  tello: TelloUnit,
                  last_task_result: str,
                  tellos: List[TelloUnit]) -> Tuple[bool, str | None]:
        index = tellos.index(tello)
        altitude = self.flight_level_1 if index % 2 == 0 else self.flight_level_2
        if tello.detected_marker != self.end_pad_no:
            return (
                True,
                f'go {self.distance_between_pads} 0 {altitude} {self.speed} m{self.path_pad_no}'
            )
        elif tello.detected_marker is None:
            # If we haven't seen a pad, try to go forward and see if we can detect one.
            return (
                True,
                self.search_for_pad(tello, altitude)
            )
        else:
            return False, None

    def search_for_pad(self, tello: TelloUnit, altitude: int) -> str:
        """
        Get the TelloUnit to do a rough grid search around the perimeter to find the pad.
        """

        movement_commands = [
            f"go 0 -5 {altitude} 5",
            f"go 5 0 {altitude} 5",
            f"go 0 5 {altitude} 5",
            f"go 0 5 {altitude} 5",
            f"go 5 0 {altitude} 5",
            f"go 0 -5 {altitude} 5",
        ]

        if self.tellos_last_search_tasks.get(tello) is None:
            self.tellos_last_search_tasks[tello] = 0
            return movement_commands[0]
        else:
            self.tellos_last_search_tasks[tello] += 1
            return movement_commands[self.tellos_last_search_tasks[tello]]
