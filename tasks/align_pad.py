from swarm import *


class AlignPadTask(SwarmTask):
    def __init__(self) -> None:
        super().__init__()

    def execute(self, tello: TelloUnit, search_altitude: int) -> str:
        print("placeholder")
