from swarm import SwarmStrategy
from tello import *


class FollowToBonusAndSearch(SwarmStrategy):
    def __init__(self,
                 num_of_search_tellos: int,
                 path_pad_nos: List[int],
                 window_pad_nos: List[int],
                 distance_between_pads: int,
                 travel_speed: int,
                 window_speed: int
                 ) -> None:
        self.count_map: Dict[TelloUnit, int] = {}
        self.num_of_search_tellos = num_of_search_tellos
        self.path_pad_nos = path_pad_nos
        self.window_pad_nos = window_pad_nos
        self.distance_between_pads = distance_between_pads
        self.travel_speed = travel_speed
        self.window_speed = window_speed

    def next_task(self,
                  tello: TelloUnit,
                  last_task_result: str,
                  tellos: List[TelloUnit]) -> Tuple[bool, str | None]:
        # Keeps track of queue
        if self.count_map.get(tello) is None:
            self.count_map[tello] = 0
        self.count_map[tello] += 1

        # Setup a queue system to identify search drones (mac/ip hashmap)
        # 
        # TODO:
        # 1. Mac and IP address hashmap
        # 2. Window algo
        # 3. Deadhead search algo
        # 4. Liftoff Algo (Sync?) (use Mac/IP hashmap?)
        #   - How to move drones from liftoff to landing
        #   - Takeoff queue

        #     print(f'sending {tello.label} forward, this is the {self.count_map[tello]}th time.')
        #     return True, f'go {self.distance} 0 0 {self.speed}'
        # else:
        #     print(f'landing {tello.label}')
        #     return False, None

    def on_tello_updated(self, tello: TelloUnit) -> bool:
        return False
