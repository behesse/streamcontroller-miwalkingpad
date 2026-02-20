from .._base.SpeedActionBase import SpeedActionBase


class SpeedUp(SpeedActionBase):
    ACTIVE_ICON = "speed-up"

    def _run_speed_command(self, step: float) -> dict:
        return self.plugin_base.backend.increase_speed(step)
