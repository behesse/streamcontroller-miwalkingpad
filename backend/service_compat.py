from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from types import MethodType

from miwalkingpad import AsyncWalkingPadService
from miwalkingpad.types.events import ErrorEvent, OperationTimingEvent


def patch_async_service(service: AsyncWalkingPadService) -> None:
    async def _run_blocking_no_thread(self_service, func, operation: str):
        start = perf_counter()
        wait_ms = 0.0
        run_ms = 0.0
        try:
            lock_wait_start = perf_counter()
            async with self_service._io_lock:
                wait_ms = (perf_counter() - lock_wait_start) * 1000.0
                run_start = perf_counter()
                # Execute inline in backend event-loop thread to avoid
                # asyncio.to_thread()/executor shutdown race in host runtime.
                result = func()
                run_ms = (perf_counter() - run_start) * 1000.0

            total_ms = (perf_counter() - start) * 1000.0
            await self_service._event_bus.publish(
                OperationTimingEvent(
                    timestamp=datetime.now(UTC),
                    operation=operation,
                    wait_ms=wait_ms,
                    run_ms=run_ms,
                    total_ms=total_ms,
                    success=True,
                )
            )
            return result
        except Exception as exc:  # noqa: BLE001
            total_ms = (perf_counter() - start) * 1000.0
            await self_service._event_bus.publish(
                OperationTimingEvent(
                    timestamp=datetime.now(UTC),
                    operation=operation,
                    wait_ms=wait_ms,
                    run_ms=run_ms,
                    total_ms=total_ms,
                    success=False,
                )
            )
            await self_service._event_bus.publish(
                ErrorEvent(timestamp=datetime.now(UTC), operation=operation, message=str(exc))
            )
            raise

    service._run_blocking = MethodType(_run_blocking_no_thread, service)

