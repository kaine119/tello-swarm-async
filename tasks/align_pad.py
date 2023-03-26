from swarm import *


class AlignPadTask(SwarmTask):
    def __init__(self,
                 speed: int,
                 distance_between_pads: int,
                 path_pad_nos: List[int],
                 end_pad_nos: List[int]) -> None:
        self.speed = speed
        self.distance_between_pads = distance_between_pads
        self.path_pad_nos = path_pad_nos
        self.end_pad_nos = end_pad_nos
        super().__init__()

    def align_yaw(self, tello: TelloUnit) -> Tuple[bool, str]:
        yaw_command = "cw" if tello.marker_yaw > 0 else "ccw"
        return (
            True,
            f'{yaw_command} {abs(tello.marker_yaw)}'
        )

    def align_pad(self, tello: TelloUnit, altitude: int) -> Tuple[bool, str]:
        if abs(tello.marker_yaw) >= 10:
            # print(
            #     f"[AlignPadTask] [{tello.ip}] Aligning yaw to path pad; current yaw {tello.marker_yaw}")
            return self.align_yaw(tello)
        else:
            if not (tello.detected_marker in self.path_pad_nos):
                print(
                    f"[AlignPadTask] Fatal error: Aligning to pad {tello.detected_marker} not within path numbers")
            return (
                True,
                f'go {self.distance_between_pads} 0 {altitude} {self.speed} m{tello.detected_marker}'
            )

    def align_end_pad(self, tello: TelloUnit, altitude: int) -> Tuple[bool, str | None]:
        marker_x, marker_y = tello.marker_xy
        if abs(marker_x) <= 10 and abs(marker_y) <= 10:
            tello.landing = True
            print(
                f"[AlignPadTask] [{tello.ip}] Successfully aligned to landing pad; current rel coordinates {tello.marker_xy}")
            return False, None
        else:
            print(
                f"[AlignPadTask] [{tello.ip}] Aligning to landing pad; current rel coordinates {tello.marker_xy}")
            return (
                True,
                f'go 0 0 {altitude} {self.speed} m{tello.detected_marker}'
            )
