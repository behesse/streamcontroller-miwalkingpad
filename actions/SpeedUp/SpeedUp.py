# Import StreamController modules
from src.backend.PluginManager.ActionBase import ActionBase

import os
from loguru import logger as log


class SpeedUp(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_ready(self) -> None:
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "treadmill-offline.svg")
        self.set_media(media_path=icon_path, size=0.75)
        self._refresh_speed_label()

    def on_tick(self) -> None:
        self._refresh_speed_label()

    def on_key_down(self) -> None:
        try:
            result = self.plugin_base.backend.increase_speed(0.5)
            if not result.get("ok", False):
                self.show_error()
            self._set_speed_label_from_result(result)
        except Exception as exc:
            log.error(exc)
            self.show_error()

    def _refresh_speed_label(self) -> None:
        try:
            status = self.plugin_base.backend.get_status()
            self._set_speed_label_from_result(status)
        except Exception as exc:
            log.error(exc)

    def _set_speed_label_from_result(self, payload: dict) -> None:
        connected = bool(payload.get("connected", False))
        running = bool(payload.get("running", False))

        if not connected or not running:
            self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "treadmill-offline.svg"), size=0.75)
            self.set_bottom_label("")
            return

        self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "up.svg"), size=0.75)
        speed = payload.get("speed", None)
        if speed is None:
            self.set_bottom_label("")
            return
        self.set_bottom_label(f"{float(speed):.1f} km/h")
