from .._base.SpeedActionBase import SpeedActionBase


class SpeedDown(SpeedActionBase):
    ACTIVE_ICON = "speed-down"

    def _run_speed_command(self, step: float) -> dict:
        return self.plugin_base.backend.decrease_speed(step)
