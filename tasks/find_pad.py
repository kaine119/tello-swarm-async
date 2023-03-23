from swarm import *


class FindPadTask(SwarmTask):
    def __init__(self) -> None:
        super().__init__()
        self.tellos_last_search_tasks = {}
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

    def execute(self, tello: TelloUnit, search_altitude: int) -> str:
        """
        Get the TelloUnit to do a rough grid search around the perimeter to find the pad.
        """

        movement_commands = [
            f"left 50",
            f"forward 20",
            f"right 50",
            f"right 50",
            f"forward 20",
            f"left 50",
        ]

        if self.tellos_last_search_tasks.get(tello) is None:
            self.tellos_last_search_tasks[tello] = -1
            return f"go 0 0 {search_altitude} 10"
        else:
            self.tellos_last_search_tasks[tello] += 1
            return movement_commands[self.tellos_last_search_tasks[tello] % 6]
