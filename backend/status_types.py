from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


@dataclass(slots=True)
class BackendStatusCache:
    connected: bool = False
    running: bool = False
    speed: float | None = None
    runtime_seconds: int = 0
    steps: int = 0
    distance_km: float = 0.0
    error: str = ""


class BackendStatusPayload(TypedDict):
    ok: bool
    connected: bool
    running: bool
    speed: float | None
    runtime_seconds: int
    steps: int
    distance_km: float
    error: str

