from swarm import *


class AlignPadTask(SwarmTask):
    def __init__(self) -> None:
        super().__init__()

    def align_yaw(self, tello: TelloUnit) -> Tuple[bool, str]:
        yaw_command = "cw" if tello.marker_yaw > 0 else "ccw"
        return (
            True,
            f'{yaw_command} {abs(tello.marker_yaw)}'
        )

    def align_pad(self, tello: TelloUnit, altitude: int) -> Tuple[bool, str]:
        if abs(tello.marker_yaw) >= 10:
            print(
                f"[AlignPadTask] [{tello.ip}] Aligning yaw to path pad; current yaw {tello.marker_yaw}")
            return self.align_yaw(tello)
        else:
            return (
                True,
                f'go {self.distance_between_pads} 0 {altitude} {self.speed} m{self.path_pad_no}'
            )

    def align_end_pad(self, tello: TelloUnit, altitude: int) -> Tuple[bool, str]:
        marker_x, marker_y = tello.marker_xy
        if abs(marker_x) <= 10 and abs(marker_y) <= 10:
            print(
                f"[AlignPadTask] [{tello.ip}] Successfully aligned to landing pad; current rel coordinates {tello.marker_xy}")
            return False, None
        else:
            print(
                f"[AlignPadTask] [{tello.ip}] Aligning to landing pad; current rel coordinates {tello.marker_xy}")
            return (
                True,
                f'go 0 0 {altitude} {self.speed} m{self.end_pad_no}'
            )
