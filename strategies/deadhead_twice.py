from swarm import SwarmStrategy
from tello import *


class DeadheadNTimes(SwarmStrategy):
    def __init__(self, number_of_deadheads, distance, speed) -> None:
        self.count_map: Dict[TelloUnit, int] = {}
        self.number_of_deadheads = number_of_deadheads
        self.distance = distance
        self.speed = speed

    def next_task(self,
                  tello: TelloUnit,
                  last_task_result: str,
                  tellos: List[TelloUnit]) -> Tuple[bool, str | None]:
        if self.count_map.get(tello) is None:
            self.count_map[tello] = 0
        self.count_map[tello] += 1

        if self.count_map[tello] < self.number_of_deadheads:
            print(f'sending {tello.label} forward, this is the {self.count_map[tello]}th time.')
            return True, f'go {self.distance} 0 0 {self.speed}'
        else:
            print(f'landing {tello.label}')
            return False, None

    def on_tello_updated(self, tello: TelloUnit) -> bool:
        return False
