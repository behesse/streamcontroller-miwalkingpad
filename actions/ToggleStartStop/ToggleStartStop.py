from __future__ import annotations

import os
from loguru import logger as log

from src.backend.PluginManager.ActionBase import ActionBase


class ToggleStartStop(ActionBase):
    METRIC_RUNTIME = 0
    METRIC_STEPS = 1
    METRIC_DISTANCE = 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._metric_index = self.METRIC_RUNTIME
        self._tick_counter = 0
        self._rotation_every_ticks = 3

    def on_ready(self) -> None:
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "treadmill-offline.svg")
        self.set_media(media_path=icon_path, size=0.75)
        self._refresh_from_status(rotate_metric=False)

    def on_tick(self) -> None:
        self._tick_counter += 1
        rotate_metric = self._tick_counter % self._rotation_every_ticks == 0
        self._refresh_from_status(rotate_metric=rotate_metric)

    def on_key_down(self) -> None:
        try:
            status = self.plugin_base.backend.get_status()
            is_running = bool(status.get("running", False))

            if is_running:
                result = self.plugin_base.backend.stop_belt()
            else:
                result = self.plugin_base.backend.start_belt()

            if not result.get("ok", False):
                self.show_error()

            self._refresh_from_status(rotate_metric=False)
        except Exception as exc:  # noqa: BLE001
            log.error(exc)
            self.show_error()

    def _refresh_from_status(self, rotate_metric: bool) -> None:
        try:
            status = self.plugin_base.backend.get_status()
            connected = bool(status.get("connected", False))
            running = bool(status.get("running", False))

            if connected:
                self._sync_visual_state(running)
                if running:
                    self._update_metric_labels(status=status, rotate_metric=rotate_metric)
                else:
                    self.set_top_label("")
                    self.set_bottom_label("")
            else:
                self.set_media(media_path=os.path.join(self.plugin_base.PATH, "assets", "treadmill-offline.svg"), size=0.75)
                self.set_top_label("")
                self.set_bottom_label("")
        except Exception as exc:  # noqa: BLE001
            log.error(exc)

    def _sync_visual_state(self, running: bool) -> None:
        # This action is expected to be present in two key states:
        # state 0 -> stopped, state 1 -> running.
        target_state = 1 if running else 0

        try:
            c_input = self.get_input()
            if c_input is not None and target_state in c_input.states and c_input.state != target_state:
                c_input.set_state(target_state, update_sidebar=False)
        except Exception:
            # UI state switching failure should never block control.
            pass

        icon_name = "pause.svg" if running else "treadmill.svg"
        icon_path = os.path.join(self.plugin_base.PATH, "assets", icon_name)
        self.set_media(media_path=icon_path, size=0.75)
        self.set_center_label("")

    def _update_metric_labels(self, status: dict, rotate_metric: bool) -> None:
        if rotate_metric:
            self._metric_index = (self._metric_index + 1) % 3

        if self._metric_index == self.METRIC_RUNTIME:
            runtime_seconds = int(status.get("runtime_seconds", 0))
            mins, secs = divmod(max(0, runtime_seconds), 60)
            self.set_top_label("Time")
            self.set_bottom_label(f"{mins:02d}:{secs:02d}")
            return

        if self._metric_index == self.METRIC_STEPS:
            steps = int(status.get("steps", 0))
            self.set_top_label("Steps")
            self.set_bottom_label(f"{steps}")
            return

        distance = float(status.get("distance_km", 0.0))
        self.set_top_label("Distance")
        self.set_bottom_label(f"{distance:.2f} km")
