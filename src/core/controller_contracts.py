"""Pure controller-facing contracts for deterministic tests and adapters."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .rtss_contracts import (
    RationalCap,
    RtssApplyRequest,
    RtssApplyResult,
    RtssGeneration,
    RtssReadback,
)

# Compatibility name for the initial controller harness; the canonical model
# now lives in rtss_contracts.
ControlGeneration = RtssGeneration


class Clock(Protocol):
    """A monotonic time source."""

    def monotonic(self) -> Decimal:
        """Return monotonic elapsed seconds."""


@dataclass(frozen=True, slots=True)
class FpsProcessSample:
    """One timestamped FPS and process-identity observation."""

    captured_at: Decimal
    fps: Decimal | None
    process_name: str | None
    source_generation: int
    valid: bool = True


class FpsProcessSource(Protocol):
    """Source of atomic FPS and process-identity samples."""

    def read_sample(self) -> FpsProcessSample:
        """Return the next available sample."""


@dataclass(frozen=True, slots=True)
class SensorReading:
    """One immutable sensor observation."""

    hardware_id: str
    sensor_id: str
    name: str
    sensor_type: str
    value: Decimal | None
    captured_at: Decimal
    valid: bool = True


@dataclass(frozen=True, slots=True)
class SensorSnapshot:
    """An atomic group of sensor observations from one source generation."""

    captured_at: Decimal
    source_generation: int
    readings: tuple[SensorReading, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "readings", tuple(self.readings))


class SensorSnapshotSource(Protocol):
    """Source of atomic sensor snapshots."""

    def read_snapshot(self) -> SensorSnapshot:
        """Return the next available snapshot."""


class RtssAdapter(Protocol):
    """Small generation-aware RTSS boundary for later production adapters."""

    def apply(self, request: RtssApplyRequest) -> RtssApplyResult:
        """Apply one immutable RTSS request."""

    def read(self, generation: RtssGeneration) -> RtssReadback:
        """Read cap state for the supplied immutable generation."""
