from __future__ import annotations

from loguru import logger as log

from .._base.WalkingPadActionBase import WalkingPadActionBase


class ToggleStartStop(WalkingPadActionBase):
    METRICS = ("time", "steps", "distance")
    METRIC_TIME = "time"
    METRIC_STEPS = "steps"
    METRIC_DISTANCE = "distance"
    ROTATION_EVERY_TICKS = 3
    OFFLINE_ICON = "offline"
    STOPPED_ICON = "main"
    RUNNING_ICON = "pause"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._metric_index = 0
        self._tick_counter = 0

    def on_ready(self) -> None:
        self.set_icon(self.OFFLINE_ICON)
        self._refresh_from_status(rotate_metric=False)

    def on_tick(self) -> None:
        self._tick_counter += 1
        rotate_metric = self._tick_counter % self.ROTATION_EVERY_TICKS == 0
        self._refresh_from_status(rotate_metric=rotate_metric)

    def on_key_down(self) -> None:
        try:
            backend = self.get_backend()
            if backend is None:
                self.show_error()
                self._render_offline()
                return

            status = backend.get_status()
            is_running = bool(status.get("running", False))

            if is_running:
                result = backend.stop_belt()
            else:
                result = backend.start_belt()

            if not result.get("ok", False):
                self.show_error()

            self._refresh_from_status(rotate_metric=False)
        except Exception as exc:  # noqa: BLE001
            log.error(exc)
            self.show_error()

    def _refresh_from_status(self, rotate_metric: bool) -> None:
        status = self.get_backend_status()
        if status is None:
            self._render_offline()
            return

        connected = bool(status.get("connected", False))
        running = bool(status.get("running", False))

        if not connected:
            self._render_offline()
            return

        self._sync_visual_state(running)

        if not running:
            self._render_stopped()
            return

        self._update_metric_labels(status=status, rotate_metric=rotate_metric)

    def _render_offline(self) -> None:
        self.set_icon(self.OFFLINE_ICON)
        self.clear_labels()

    def _render_stopped(self) -> None:
        self.clear_labels()

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

        self.set_icon(self.RUNNING_ICON if running else self.STOPPED_ICON)
        self.set_center_label("")

    def _update_metric_labels(self, status: dict, rotate_metric: bool) -> None:
        if rotate_metric:
            self._metric_index = (self._metric_index + 1) % len(self.METRICS)

        metric = self.METRICS[self._metric_index]

        if metric == self.METRIC_TIME:
            runtime_seconds = int(status.get("runtime_seconds", 0))
            total_minutes = max(0, runtime_seconds) // 60
            hours, minutes = divmod(total_minutes, 60)
            self.set_top_label("Time")
            self.set_bottom_label(f"{hours:02d}:{minutes:02d}")
            return

        if metric == self.METRIC_STEPS:
            steps = int(status.get("steps", 0))
            self.set_top_label("Steps")
            self.set_bottom_label(f"{steps}")
            return

        distance = float(status.get("distance_km", 0.0))
        self.set_top_label("Distance")
        self.set_bottom_label(f"{distance:.2f} km")
