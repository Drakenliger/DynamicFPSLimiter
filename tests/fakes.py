"""Deterministic fakes for pure controller and adapter tests."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from src.core.controller_contracts import FpsProcessSample, SensorSnapshot
from src.core.rtss_contracts import (
    CanonicalProfileIdentity,
    RtssApplyRequest,
    RtssApplyResult,
    RtssGeneration,
    RtssReadback,
)


def _exact_decimal(value: int | Decimal, *, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise TypeError(f"{label} must be an exact int or Decimal")
    converted = Decimal(value)
    if not converted.is_finite():
        raise ValueError(f"{label} must be finite")
    return converted


class FakeClock:
    """Manually advanced monotonic clock."""

    def __init__(self, start: int | Decimal = 0) -> None:
        self._now = _exact_decimal(start, label="start")

    def monotonic(self) -> Decimal:
        return self._now

    def advance(self, seconds: int | Decimal) -> Decimal:
        increment = _exact_decimal(seconds, label="seconds")
        if increment < 0:
            raise ValueError("seconds must not be negative")
        self._now += increment
        return self._now


class ScriptedFpsProcessSource:
    """Return FPS/process samples in a fixed order."""

    def __init__(self, samples: Iterable[FpsProcessSample]) -> None:
        self._samples = tuple(samples)
        self._index = 0

    def read_sample(self) -> FpsProcessSample:
        if self._index >= len(self._samples):
            raise RuntimeError("scripted FPS/process samples exhausted")
        sample = self._samples[self._index]
        self._index += 1
        return sample


class ScriptedSensorSource:
    """Return sensor snapshots in a fixed order."""

    def __init__(self, snapshots: Iterable[SensorSnapshot]) -> None:
        self._snapshots = tuple(snapshots)
        self._index = 0

    def read_snapshot(self) -> SensorSnapshot:
        if self._index >= len(self._snapshots):
            raise RuntimeError("scripted sensor snapshots exhausted")
        snapshot = self._snapshots[self._index]
        self._index += 1
        return snapshot


class FakeRtssAdapter:
    """Queue RTSS results and record all requests in exact call order."""

    def __init__(
        self,
        *,
        apply_results: Iterable[RtssApplyResult] = (),
        readback_results: Iterable[RtssReadback] = (),
    ) -> None:
        self._apply_results = tuple(apply_results)
        self._readback_results = tuple(readback_results)
        self._apply_index = 0
        self._readback_index = 0
        self.requests: list[tuple[str, RtssApplyRequest | RtssGeneration]] = []

    def apply(self, request: RtssApplyRequest) -> RtssApplyResult:
        self.requests.append(("apply", request))
        if self._apply_index >= len(self._apply_results):
            raise RuntimeError("scripted RTSS apply results exhausted")
        result = self._apply_results[self._apply_index]
        self._apply_index += 1
        return result

    def read(self, generation: RtssGeneration) -> RtssReadback:
        self.requests.append(("read", generation))
        if self._readback_index >= len(self._readback_results):
            raise RuntimeError("scripted RTSS readback results exhausted")
        result = self._readback_results[self._readback_index]
        self._readback_index += 1
        return result


class FakeGenerationFactory:
    """Create immutable generation tokens whose dimensions vary independently."""

    def __init__(
        self,
        *,
        application_generation: int = 1,
        session_generation: int = 1,
        profile_generation: int = 1,
        source_generation: int = 1,
    ) -> None:
        self.application_generation = application_generation
        self.session_generation = session_generation
        self.profile_generation = profile_generation
        self.source_generation = source_generation

    def create(self, profile_identity: str) -> RtssGeneration:
        return RtssGeneration(
            application_generation=self.application_generation,
            session_generation=self.session_generation,
            profile_generation=self.profile_generation,
            profile_identity=CanonicalProfileIdentity.from_legacy_name(
                profile_identity
            ),
            source_generation=self.source_generation,
        )

    def advance_session(self) -> int:
        self.session_generation += 1
        return self.session_generation

    def advance_profile(self) -> int:
        self.profile_generation += 1
        return self.profile_generation

    def advance_source(self) -> int:
        self.source_generation += 1
        return self.source_generation
