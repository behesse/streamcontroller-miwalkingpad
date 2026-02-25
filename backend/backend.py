from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from datetime import timedelta

from loguru import logger as log
from streamcontroller_plugin_tools import BackendBase

from miwalkingpad import AsyncWalkingPadService, WalkingPadAdapter
from miwalkingpad.discovery import discover_handshake

try:
    from .service_compat import patch_async_service
    from .status_types import BackendStatusCache, BackendStatusPayload
except ImportError:
    # Allow direct script execution (no package context)
    from service_compat import patch_async_service
    from status_types import BackendStatusCache, BackendStatusPayload


class WalkingPadBackend(BackendBase):
    RETRY_SECONDS = 5.0
    POLL_SECONDS = 5.0
    MIN_SPEED = 0.0
    MAX_SPEED = 6.0
    MODEL = "ksmb.walkingpad.v1"

    @staticmethod
    def _is_not_supported_error(exc: Exception) -> bool:
        return "not_supported" in str(exc).lower()

    def __init__(self) -> None:
        super().__init__()

        self._stop_event = threading.Event()
        self._main_exit_event = threading.Event()

        self._config_lock = threading.Lock()
        self._ip = ""
        self._token = ""
        self._device_id = ""

        self._status_cache = BackendStatusCache()

        self._loop = None
        self._loop_thread = None
        self._start_loop_thread()

        self._service: AsyncWalkingPadService | None = None
        self._connection_task = asyncio.run_coroutine_threadsafe(self._connection_worker(), self._loop)

    def _start_loop_thread(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=False, name="miwalkingpad-loop")
        self._loop_thread.start()

    def _stop_loop_thread(self) -> None:
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if (
            self._loop_thread is not None
            and self._loop_thread.is_alive()
            and threading.current_thread() is not self._loop_thread
        ):
            self._loop_thread.join(timeout=1)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_coro(self, coro, timeout: float = 20.0):
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout)

    def _set_disconnected(self, reason: str) -> None:
        self._status_cache.connected = False
        self._status_cache.running = False
        self._status_cache.error = reason

    def _update_cached_status_fields(self, status) -> None:
        # Primary extraction based on py-miwalkingpad PadStatus contract.
        speed = getattr(status, "speed_kmh", None)
        if speed is not None:
            self._status_cache.speed = float(speed)

        is_on = getattr(status, "is_on", None)
        if is_on is not None:
            self._status_cache.running = bool(is_on) and (self._status_cache.speed or 0.0) > 0.01
        elif self._status_cache.speed is not None:
            self._status_cache.running = self._status_cache.speed > 0.01

        walking_time = getattr(status, "walking_time", None)
        if isinstance(walking_time, timedelta):
            self._status_cache.runtime_seconds = max(0, int(walking_time.total_seconds()))

        step_count = getattr(status, "step_count", None)
        if step_count is not None:
            self._status_cache.steps = max(0, int(step_count))

        distance_m = getattr(status, "distance_m", None)
        if distance_m is not None:
            self._status_cache.distance_km = max(0.0, float(distance_m) / 1000.0)

    def _read_config(self) -> tuple[str, str, str]:
        with self._config_lock:
            return self._ip, self._token, self._device_id

    def _resolve_ip_from_discovery(self, device_id: str) -> str | None:
        try:
            found = discover_handshake(timeout=max(1, int(self.RETRY_SECONDS)), token=None)
        except Exception as exc:  # noqa: BLE001
            log.warning(f"WalkingPad discovery failed: {exc}")
            return None

        wanted = (device_id or "").strip().lower()
        if not wanted:
            return None

        for entry in found:
            entry_device_id = str(getattr(entry, "device_id", "") or "").strip().lower()
            entry_ip = str(getattr(entry, "ip", "") or "").strip()
            if entry_device_id == wanted and entry_ip:
                return entry_ip
        return None

    async def _connection_worker(self) -> None:
        active_cfg: tuple[str, str] | None = None

        while not self._stop_event.is_set():
            configured_ip, token, device_id = self._read_config()

            token_value = (token or "").strip()
            if not token_value:
                self._service = None
                self._set_disconnected("missing_config")
                await asyncio.sleep(self.RETRY_SECONDS)
                continue

            resolved_ip = configured_ip
            if not resolved_ip and device_id:
                discovered_ip = self._resolve_ip_from_discovery(device_id)
                if discovered_ip is None:
                    self._service = None
                    self._set_disconnected("device_not_found")
                    await asyncio.sleep(self.RETRY_SECONDS)
                    continue
                resolved_ip = discovered_ip

            cfg = (resolved_ip, token_value)

            if not resolved_ip:
                self._service = None
                self._set_disconnected("missing_config")
                await asyncio.sleep(self.RETRY_SECONDS)
                continue

            if active_cfg != cfg or self._service is None:
                try:
                    adapter = WalkingPadAdapter(ip=resolved_ip, token=token_value, model=self.MODEL)
                    service = AsyncWalkingPadService(adapter=adapter)
                    patch_async_service(service)
                    status = await self._get_status_safe(service)
                    self._service = service
                    active_cfg = cfg
                    self._status_cache.connected = True
                    self._status_cache.error = ""
                    self._update_cached_status_fields(status)
                    log.info("WalkingPad backend connected")
                except Exception as exc:  # noqa: BLE001
                    self._service = None
                    self._set_disconnected(str(exc))
                    log.warning(f"WalkingPad connect failed: {exc}")
                    await asyncio.sleep(self.RETRY_SECONDS)
                    continue

            try:
                status = await self._get_status_safe(self._service)
                self._status_cache.connected = True
                self._status_cache.error = ""
                self._update_cached_status_fields(status)
            except Exception as exc:  # noqa: BLE001
                self._set_disconnected(str(exc))
                self._service = None
                log.warning(f"WalkingPad connection lost: {exc}")
                await asyncio.sleep(self.RETRY_SECONDS)
                continue

            await asyncio.sleep(self.POLL_SECONDS)

    def _request_stop(self) -> None:
        if self._stop_event.is_set():
            return

        self._stop_event.set()

        if self._connection_task is not None:
            self._connection_task.cancel()

            # Let cancellation settle before stopping the loop to avoid
            # "Task was destroyed but it is pending" on shutdown.
            try:
                self._connection_task.result(timeout=2)
            except (concurrent.futures.CancelledError, concurrent.futures.TimeoutError):
                pass
            except Exception:
                pass

        self._stop_loop_thread()

        self._main_exit_event.set()

    def on_disconnect(self, conn) -> None:
        self._request_stop()
        super().on_disconnect(conn)

    async def _get_status_safe(self, service: AsyncWalkingPadService):
        try:
            return await service.get_status(quick=False)
        except Exception as exc:  # noqa: BLE001
            if self._is_not_supported_error(exc):
                return await service.get_status(quick=True)
            raise

    async def _require_connected(self) -> None:
        if self._service is None or not self._status_cache.connected:
            raise RuntimeError("walkingpad_not_connected")

    @staticmethod
    def _clamp(speed: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, speed))

    def configure(self, ip: str, token: str, device_id: str = "") -> dict:
        with self._config_lock:
            self._ip = (ip or "").strip()
            self._token = (token or "").strip()
            self._device_id = (device_id or "").strip()

        # Force reconnect on updated credentials.
        self._service = None
        self._status_cache.connected = False
        return self.get_status()

    def discover_devices(self, token: str, timeout: int = 5) -> dict:
        token_value = (token or "").strip()
        if not token_value:
            return {"ok": False, "error": "token_required", "devices": []}

        try:
            found = discover_handshake(timeout=max(1, int(timeout)), token=token_value)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "devices": []}

        devices: list[dict] = []
        for entry in found:
            info = getattr(entry, "info", None) or {}
            model = str(info.get("model", "") or "")
            is_walkingpad = "walkingpad" in model.lower()
            if not is_walkingpad:
                continue

            devices.append(
                {
                    "ip": str(getattr(entry, "ip", "") or ""),
                    "device_id": str(getattr(entry, "device_id", "") or ""),
                    "token": str(getattr(entry, "token", "") or ""),
                    "auth_ok": bool(getattr(entry, "auth_ok", False)),
                    "auth_error": getattr(entry, "auth_error", None),
                    "model": model,
                }
            )

        return {"ok": True, "devices": devices}

    async def _start_belt_async(self) -> dict:
        await self._require_connected()
        await self._service.start()
        self._status_cache.running = True
        return self.get_status() | {"ok": True}

    async def _stop_belt_async(self) -> dict:
        await self._require_connected()
        await self._service.stop()
        self._status_cache.running = False
        return self.get_status() | {"ok": True}

    async def _speed_delta_async(self, delta: float) -> dict:
        await self._require_connected()
        running_now = self._status_cache.running

        if self._status_cache.speed is None:
            raise RuntimeError("walkingpad_speed_unavailable")

        current_speed = float(self._status_cache.speed)

        # Do not alter device start-speed configuration when belt is stopped.
        # Speed +/- actions become a no-op in stopped state.
        if not running_now:
            return self.get_status() | {"ok": True}

        target_speed = self._clamp(current_speed + delta, self.MIN_SPEED, self.MAX_SPEED)
        await self._service.set_speed(target_speed)

        self._status_cache.speed = target_speed
        if target_speed <= 0.0:
            self._status_cache.running = False
        return self.get_status() | {"ok": True}

    def _run_command(self, coro) -> dict:
        try:
            return self._run_coro(coro)
        except Exception as exc:  # noqa: BLE001
            # Command failures (for example user-ack timeouts) should not
            # force the backend into disconnected state. Connection health is
            # tracked by the polling loop.
            return self.get_status() | {"ok": False, "error": str(exc)}

    def start_belt(self) -> dict:
        return self._run_command(self._start_belt_async())

    def stop_belt(self) -> dict:
        return self._run_command(self._stop_belt_async())

    def increase_speed(self, step: float = 0.5) -> dict:
        return self._run_command(self._speed_delta_async(abs(float(step))))

    def decrease_speed(self, step: float = 0.5) -> dict:
        return self._run_command(self._speed_delta_async(-abs(float(step))))

    def get_status(self) -> BackendStatusPayload:
        return {
            "ok": self._status_cache.connected,
            "connected": self._status_cache.connected,
            "running": self._status_cache.running,
            "speed": round(float(self._status_cache.speed), 2) if self._status_cache.speed is not None else None,
            "runtime_seconds": int(self._status_cache.runtime_seconds),
            "steps": int(self._status_cache.steps),
            "distance_km": round(float(self._status_cache.distance_km), 3),
            "error": self._status_cache.error,
        }


backend = WalkingPadBackend()

# Keep the main thread alive.
# If the module exits immediately, Python starts interpreter shutdown,
# which flips the global threadpool shutdown flag used by asyncio.to_thread()
# inside AsyncWalkingPadService.
if __name__ == "__main__":
    try:
        backend._main_exit_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        backend._request_stop()
