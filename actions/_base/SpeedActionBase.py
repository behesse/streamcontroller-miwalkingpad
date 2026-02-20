from __future__ import annotations

from loguru import logger as log

from .WalkingPadActionBase import WalkingPadActionBase


class SpeedActionBase(WalkingPadActionBase):
    STEP = 0.5
    OFFLINE_ICON = "offline"
    ACTIVE_ICON = ""

    def on_ready(self) -> None:
        self.set_icon(self.OFFLINE_ICON)
        self._refresh_speed_label()

    def on_tick(self) -> None:
        self._refresh_speed_label()

    def on_key_down(self) -> None:
        try:
            backend = self.get_backend()
            if backend is None:
                self.show_error()
                self.set_icon(self.OFFLINE_ICON)
                return

            result = self._run_speed_command(self.STEP)
            if not result.get("ok", False):
                self.show_error()
            self._set_speed_label_from_result(result)
        except Exception as exc:  # noqa: BLE001
            log.error(exc)
            self.show_error()

    def _refresh_speed_label(self) -> None:
        status = self.get_backend_status()
        if status is None:
            self.set_icon(self.OFFLINE_ICON)
            self.set_bottom_label("")
            return
        self._set_speed_label_from_result(status)

    def _set_speed_label_from_result(self, payload: dict) -> None:
        connected = bool(payload.get("connected", False))
        running = bool(payload.get("running", False))

        if not connected or not running:
            self.set_icon(self.OFFLINE_ICON)
            self.set_bottom_label("")
            return

        self.set_icon(self.ACTIVE_ICON)
        speed = payload.get("speed", None)
        if speed is None:
            self.set_bottom_label("")
            return
        self.set_bottom_label(f"{float(speed):.1f} km/h")

    def _run_speed_command(self, step: float) -> dict:
        raise NotImplementedError
