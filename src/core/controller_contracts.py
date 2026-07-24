"""Pure controller-facing contracts for deterministic tests and adapters."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


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


@dataclass(frozen=True, slots=True)
class RationalCap:
    """An exact rational RTSS cap."""

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if isinstance(self.numerator, bool) or not isinstance(self.numerator, int):
            raise TypeError("numerator must be an exact int")
        if isinstance(self.denominator, bool) or not isinstance(self.denominator, int):
            raise TypeError("denominator must be an exact int")
        if self.denominator == 0:
            raise ValueError("denominator must not be zero")

    @property
    def value(self) -> Decimal:
        """Return the exact decimal value represented by this cap."""

        return Decimal(self.numerator) / Decimal(self.denominator)


@dataclass(frozen=True, slots=True)
class ControlGeneration:
    """Immutable identity for application, session, profile, and source state."""

    application_generation: int
    session_generation: int
    profile_generation: int
    source_generation: int
    profile_identity: str


@dataclass(frozen=True, slots=True)
class RtssReadbackResult:
    """Result of reading cap state from RTSS."""

    succeeded: bool
    cap: RationalCap | None
    limiter_flags: int | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class RtssApplyResult:
    """Result of applying a requested cap and optionally reading it back."""

    succeeded: bool
    requested_cap: RationalCap
    readback: RtssReadbackResult | None
    error: str | None = None


class RtssAdapter(Protocol):
    """Small generation-aware RTSS boundary for later production adapters."""

    def apply_cap(
        self,
        generation: ControlGeneration,
        cap: RationalCap,
    ) -> RtssApplyResult:
        """Apply a cap for the supplied immutable generation."""

    def read_cap(self, generation: ControlGeneration) -> RtssReadbackResult:
        """Read cap state for the supplied immutable generation."""
