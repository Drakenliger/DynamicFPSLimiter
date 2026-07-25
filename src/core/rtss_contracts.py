"""Pure RTSS identities, exact values, and transaction result contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, unique
from hashlib import sha256
from math import gcd
from types import MappingProxyType
from typing import Iterable


@unique
class ProfileKind(Enum):
    """The two RTSS profile identity forms supported by the application."""

    GLOBAL = "global"
    APPLICATION = "application"


@unique
class RtssDenominatorStrategy(Enum):
    """Explicit fractional-cap mechanisms; selection belongs to composition."""

    UNRESOLVED = "unresolved"
    PROFILE_FILE = "profile_file"
    RTSS_API = "rtss_api"


@unique
class RtssOutcome(Enum):
    """Structured terminal outcomes for later transaction coordination."""

    VERIFIED = "verified"
    REJECTED_VALIDATION = "rejected_validation"
    STALE_GENERATION = "stale_generation"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    POLICY_REQUIRED = "policy_required"
    CONFLICT = "conflict"
    FAILED = "failed"
    FAILED_ROLLED_BACK = "failed_rolled_back"
    DEGRADED = "degraded"


@unique
class RtssFailureStep(Enum):
    """The transaction step at which an operation stopped."""

    NONE = "none"
    VALIDATE = "validate"
    GENERATION = "generation"
    CAPABILITY = "capability"
    CAPTURE = "capture"
    APPLY = "apply"
    SAVE = "save"
    UPDATE = "update"
    READBACK = "readback"
    ROLLBACK = "rollback"
    RESTORE = "restore"
    DELETE = "delete"
    CONFLICT = "conflict"


@unique
class RtssFieldAvailability(Enum):
    """Explicit evidence state for optional document-backed profile fields."""

    NOT_REQUESTED = "not_requested"
    AVAILABLE = "available"
    READ_FAILED = "read_failed"
    UNSUPPORTED = "unsupported"
    VERIFIED_ABSENT = "verified_absent"


@unique
class RtssOwnedField(Enum):
    """Fields whose restoration can remain unresolved after an owned operation."""

    EXACT_STORED_NUMERATOR = "exact_stored_numerator"
    EXACT_STORED_DENOMINATOR = "exact_stored_denominator"
    EFFECTIVE_CAP = "effective_cap"
    PROFILE_EXISTENCE = "profile_existence"
    PROFILE_DELETION = "profile_deletion"
    VERIFIED_PROFILE_ABSENCE = "verified_profile_absence"
    PROFILE_DOCUMENT = "profile_document"
    PROFILE_REVISION = "profile_revision"
    LIMITER_FLAGS = "limiter_flags"
    SAVE = "save"
    ACTIVATION = "activation"
    BACKEND_EPOCH = "backend_epoch"
    RETAINED_OWNERSHIP = "retained_ownership"


@unique
class RtssOperationState(Enum):
    """Evidence for whether a save or activation operation is settled."""

    NOT_APPLICABLE = "not_applicable"
    VERIFIED = "verified"
    UNCERTAIN = "uncertain"


@unique
class RtssDegradedClassification(Enum):
    """Closed reasons that prevent ordinary exact ownership release."""

    PARTIAL_RESTORATION = "partial_restoration"
    UNRESOLVED_MUTATION = "unresolved_mutation"
    EXTERNAL_CONFLICT = "external_conflict"
    EVIDENCE_UNAVAILABLE = "evidence_unavailable"
    READ_FAILURE = "read_failure"


@unique
class RtssHandoffDecision(Enum):
    """Explicit recipient decision for a complete degraded handoff."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


@unique
class RtssOwnershipReleaseReason(Enum):
    """The only proofs that can release deterministic RTSS ownership."""

    EXACT_RESTORATION = "exact_restoration"
    ACCEPTED_HANDOFF = "accepted_handoff"


@unique
class _RtssRestoreDisposition(Enum):
    """Closed restore-result states used to fail new outcomes safely."""

    VERIFIED = "verified"
    PRE_MUTATION_FAILED = "pre_mutation_failed"
    UNRESOLVED = "unresolved"
    INVALID = "invalid"


@unique
class RtssStoredFieldKind(Enum):
    """The two independently observed fields in an exact stored cap."""

    NUMERATOR = "numerator"
    DENOMINATOR = "denominator"


@unique
class RtssStoredCapStatus(Enum):
    """Derived pair state; applicability is separate from observation success."""

    NOT_REQUESTED = "not_requested"
    CAPTURED = "captured"
    CAPTURE_FAILED = "capture_failed"
    UNSUPPORTED = "unsupported"
    VERIFIED_ABSENT = "verified_absent"
    INCONSISTENT = "inconsistent"


_RESTORE_OUTCOME_DISPOSITIONS = {
    RtssOutcome.VERIFIED: _RtssRestoreDisposition.VERIFIED,
    RtssOutcome.REJECTED_VALIDATION: _RtssRestoreDisposition.INVALID,
    RtssOutcome.STALE_GENERATION: _RtssRestoreDisposition.INVALID,
    RtssOutcome.UNSUPPORTED_CAPABILITY: _RtssRestoreDisposition.UNRESOLVED,
    RtssOutcome.POLICY_REQUIRED: _RtssRestoreDisposition.INVALID,
    RtssOutcome.CONFLICT: _RtssRestoreDisposition.UNRESOLVED,
    RtssOutcome.FAILED: _RtssRestoreDisposition.PRE_MUTATION_FAILED,
    RtssOutcome.FAILED_ROLLED_BACK: _RtssRestoreDisposition.INVALID,
    RtssOutcome.DEGRADED: _RtssRestoreDisposition.UNRESOLVED,
}
_RESTORE_PRE_MUTATION_FAILURE_STEPS = frozenset(
    {
        RtssFailureStep.VALIDATE,
        RtssFailureStep.GENERATION,
        RtssFailureStep.CAPABILITY,
        RtssFailureStep.CAPTURE,
    }
)
_RESTORE_POST_MUTATION_FAILURE_STEPS = frozenset(
    {
        RtssFailureStep.APPLY,
        RtssFailureStep.SAVE,
        RtssFailureStep.UPDATE,
        RtssFailureStep.READBACK,
        RtssFailureStep.ROLLBACK,
        RtssFailureStep.RESTORE,
        RtssFailureStep.DELETE,
    }
)
_RESTORE_REQUIRED_FAILURE_STEPS = {
    RtssOutcome.UNSUPPORTED_CAPABILITY: frozenset(
        {RtssFailureStep.CAPABILITY}
    ),
    RtssOutcome.CONFLICT: frozenset({RtssFailureStep.CONFLICT}),
    RtssOutcome.FAILED: _RESTORE_PRE_MUTATION_FAILURE_STEPS,
    RtssOutcome.DEGRADED: _RESTORE_POST_MUTATION_FAILURE_STEPS,
}


RTSS_READBACK_OUTCOMES = frozenset(
    {
        RtssOutcome.VERIFIED,
        RtssOutcome.REJECTED_VALIDATION,
        RtssOutcome.STALE_GENERATION,
        RtssOutcome.UNSUPPORTED_CAPABILITY,
        RtssOutcome.POLICY_REQUIRED,
        RtssOutcome.CONFLICT,
        RtssOutcome.FAILED,
    }
)
RTSS_READBACK_FAILURE_STEPS = frozenset(
    {
        RtssFailureStep.NONE,
        RtssFailureStep.VALIDATE,
        RtssFailureStep.GENERATION,
        RtssFailureStep.CAPABILITY,
        RtssFailureStep.READBACK,
        RtssFailureStep.CONFLICT,
    }
)
_READBACK_FAILURE_STEPS_BY_OUTCOME = MappingProxyType(
    {
        RtssOutcome.VERIFIED: frozenset({RtssFailureStep.NONE}),
        RtssOutcome.REJECTED_VALIDATION: frozenset(
            {RtssFailureStep.VALIDATE}
        ),
        RtssOutcome.STALE_GENERATION: frozenset(
            {RtssFailureStep.GENERATION}
        ),
        RtssOutcome.UNSUPPORTED_CAPABILITY: frozenset(
            {RtssFailureStep.CAPABILITY}
        ),
        RtssOutcome.POLICY_REQUIRED: frozenset(
            {RtssFailureStep.CAPABILITY}
        ),
        RtssOutcome.CONFLICT: frozenset({RtssFailureStep.CONFLICT}),
        RtssOutcome.FAILED: frozenset({RtssFailureStep.READBACK}),
    }
)


_GLOBAL_PROFILE_NAME = "Global"
_DEFAULT_MAXIMUM_ABSOLUTE_DECIMAL_EXPONENT = 1000
_DEFAULT_MAXIMUM_DECIMAL_SIGNIFICANT_DIGITS = 1000
_DEFAULT_MAXIMUM_NUMERATOR_BITS = 4096
_DEFAULT_MAXIMUM_DENOMINATOR_BITS = 4096
_INVALID_WINDOWS_FILENAME_CHARACTERS = frozenset('<>:"/\\|?*')
_RESERVED_WINDOWS_STEMS = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "CLOCK$",
        "CONIN$",
        "CONOUT$",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)


def _require_plain_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    return value


def _require_nonnegative_int(value: object, *, label: str) -> int:
    converted = _require_plain_int(value, label=label)
    if converted < 0:
        raise ValueError(f"{label} must not be negative")
    return converted


def _require_positive_int(value: object, *, label: str) -> int:
    converted = _require_plain_int(value, label=label)
    if converted <= 0:
        raise ValueError(f"{label} must be positive")
    return converted


def _require_nonempty_string(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    if not value.strip():
        raise ValueError(f"{label} must not be empty or whitespace")
    return value


def _validate_outcome_details(
    outcome: RtssOutcome,
    failure_step: RtssFailureStep,
    error: str | None,
    *,
    label: str,
) -> None:
    if outcome is RtssOutcome.VERIFIED:
        if failure_step is not RtssFailureStep.NONE:
            raise ValueError(f"verified {label} must not have a failure step")
        if error is not None:
            raise ValueError(f"verified {label} must not have an error")
        return
    if failure_step is RtssFailureStep.NONE:
        raise ValueError(f"non-verified {label} requires a failure step")
    _require_nonempty_string(error, label=f"{label} error")


def _validate_optional_integer_bounds(
    minimum: int | None,
    maximum: int | None,
    *,
    label: str,
    positive: bool = False,
) -> None:
    if minimum is not None:
        _require_plain_int(minimum, label=f"minimum_{label}")
        if positive and minimum <= 0:
            raise ValueError(f"minimum_{label} must be positive")
    if maximum is not None:
        _require_plain_int(maximum, label=f"maximum_{label}")
        if positive and maximum <= 0:
            raise ValueError(f"maximum_{label} must be positive")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError(f"minimum_{label} must not exceed maximum_{label}")


def _validate_application_profile_name(name: object) -> str:
    if not isinstance(name, str):
        raise TypeError("application profile name must be a string")
    if not name:
        raise ValueError("application profile name must not be empty")
    if name != name.strip():
        raise ValueError(
            "application profile name must not have leading or trailing whitespace"
        )
    if not name.isascii():
        raise ValueError("application profile name must contain ASCII characters only")
    if any(ord(character) < 32 or ord(character) == 127 for character in name):
        raise ValueError("application profile name must not contain control characters")
    if any(character in _INVALID_WINDOWS_FILENAME_CHARACTERS for character in name):
        raise ValueError(
            "application profile name must be a single Windows filename"
        )
    if name.endswith("."):
        raise ValueError("application profile name must not end with a dot")
    if name in {".", ".."}:
        raise ValueError("application profile name must not be a dot path component")
    if not name.casefold().endswith(".exe"):
        raise ValueError("application profile name must end with .exe")

    executable_stem = name[:-4]
    if executable_stem in {"", ".", ".."}:
        raise ValueError("application profile name must have an executable basename")

    windows_device_stem = executable_stem.split(".", 1)[0].rstrip(" .").upper()
    if windows_device_stem in _RESERVED_WINDOWS_STEMS:
        raise ValueError("application profile name uses a reserved Windows device name")

    return name


@dataclass(frozen=True, slots=True, eq=False)
class CanonicalProfileIdentity:
    """A validated RTSS profile identity with safely derived adapter names."""

    kind: ProfileKind
    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ProfileKind):
            raise TypeError("kind must be a ProfileKind")
        if self.kind is ProfileKind.GLOBAL:
            if self.name != _GLOBAL_PROFILE_NAME:
                raise ValueError("Global identity must use the canonical name 'Global'")
            return
        _validate_application_profile_name(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CanonicalProfileIdentity):
            return NotImplemented
        return self.canonical_key == other.canonical_key

    def __hash__(self) -> int:
        return hash((CanonicalProfileIdentity, self.canonical_key))

    @classmethod
    def global_profile(cls) -> CanonicalProfileIdentity:
        """Create the explicit Global identity."""

        return cls(ProfileKind.GLOBAL, _GLOBAL_PROFILE_NAME)

    @classmethod
    def application(cls, name: str) -> CanonicalProfileIdentity:
        """Validate and create one executable-profile identity."""

        return cls(ProfileKind.APPLICATION, _validate_application_profile_name(name))

    @classmethod
    def from_legacy_name(cls, name: str) -> CanonicalProfileIdentity:
        """Translate a legacy name without treating an empty name as Global."""

        if not isinstance(name, str):
            raise TypeError("legacy profile name must be a string")
        if not name:
            raise ValueError("legacy profile name must not be empty")
        if name.casefold() == _GLOBAL_PROFILE_NAME.casefold():
            return cls.global_profile()
        return cls.application(name)

    @property
    def canonical_key(self) -> str:
        """Return a case-insensitive identity key for collision detection."""

        if self.kind is ProfileKind.GLOBAL:
            return "global"
        return f"application:{self.name.casefold()}"

    @property
    def dll_name(self) -> bytes:
        """Return the RTSS DLL profile name derived from this identity."""

        if self.kind is ProfileKind.GLOBAL:
            return b""
        return self.name.encode("ascii")

    @property
    def relative_profile_filename(self) -> str:
        """Return the single relative filename used by a profile-file strategy."""

        if self.kind is ProfileKind.GLOBAL:
            return _GLOBAL_PROFILE_NAME
        return f"{self.name}.cfg"


def canonicalize_profile_collection(
    names: Iterable[str],
) -> tuple[CanonicalProfileIdentity, ...]:
    """Validate legacy names and reject duplicate or case-only identities."""

    if isinstance(names, (str, bytes)):
        raise TypeError("profile collection must be an iterable of names")

    identities: list[CanonicalProfileIdentity] = []
    source_names_by_key: dict[str, str] = {}
    for name in names:
        identity = CanonicalProfileIdentity.from_legacy_name(name)
        previous_name = source_names_by_key.get(identity.canonical_key)
        if previous_name is not None:
            if previous_name == name:
                raise ValueError(f"duplicate profile identity: {name}")
            raise ValueError(
                "ambiguous case-only profile identities: "
                f"{previous_name!r} and {name!r}"
            )
        source_names_by_key[identity.canonical_key] = name
        identities.append(identity)
    return tuple(identities)


@dataclass(frozen=True, slots=True)
class RationalCap:
    """An exact, reduced rational RTSS cap."""

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        numerator = _require_plain_int(self.numerator, label="numerator")
        denominator = _require_plain_int(self.denominator, label="denominator")
        if denominator <= 0:
            raise ValueError("denominator must be a positive integer")

        divisor = gcd(abs(numerator), denominator)
        object.__setattr__(self, "numerator", numerator // divisor)
        object.__setattr__(self, "denominator", denominator // divisor)

    @classmethod
    def from_value(
        cls,
        value: int | Decimal,
        *,
        maximum_absolute_exponent: int = (
            _DEFAULT_MAXIMUM_ABSOLUTE_DECIMAL_EXPONENT
        ),
        maximum_significant_digits: int = (
            _DEFAULT_MAXIMUM_DECIMAL_SIGNIFICANT_DIGITS
        ),
        maximum_numerator_bits: int = _DEFAULT_MAXIMUM_NUMERATOR_BITS,
        maximum_denominator_bits: int = _DEFAULT_MAXIMUM_DENOMINATOR_BITS,
        minimum_numerator: int | None = None,
        maximum_numerator: int | None = None,
        minimum_denominator: int | None = None,
        maximum_denominator: int | None = None,
        minimum_effective_cap: RationalCap | int | Decimal | None = None,
        maximum_effective_cap: RationalCap | int | Decimal | None = None,
        minimum_effective_cap_inclusive: bool = True,
        maximum_effective_cap_inclusive: bool = True,
    ) -> RationalCap:
        """Convert exactly within parser-safety and caller capability limits.

        The construction defaults bound parser resource use only. They are not
        RTSS capability limits and callers may replace them with stricter
        values learned from an adapter or configuration boundary.
        """

        if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
            raise TypeError("cap value must be an integer or Decimal")
        maximum_absolute_exponent = _require_nonnegative_int(
            maximum_absolute_exponent, label="maximum_absolute_exponent"
        )
        maximum_significant_digits = _require_positive_int(
            maximum_significant_digits, label="maximum_significant_digits"
        )
        maximum_numerator_bits = _require_positive_int(
            maximum_numerator_bits, label="maximum_numerator_bits"
        )
        maximum_denominator_bits = _require_positive_int(
            maximum_denominator_bits, label="maximum_denominator_bits"
        )

        if isinstance(value, Decimal):
            if not value.is_finite():
                raise ValueError("cap value must be finite")
            decimal_tuple = value.as_tuple()
            if abs(decimal_tuple.exponent) > maximum_absolute_exponent:
                raise ValueError(
                    "cap Decimal exponent exceeds the parser-safety limit"
                )
            if len(decimal_tuple.digits) > maximum_significant_digits:
                raise ValueError(
                    "cap Decimal significant digits exceed the parser-safety limit"
                )
            if any(decimal_tuple.digits):
                first_nonzero = next(
                    index
                    for index, digit in enumerate(decimal_tuple.digits)
                    if digit
                )
                if decimal_tuple.exponent >= 0:
                    minimum_decimal_digits = (
                        len(decimal_tuple.digits)
                        - first_nonzero
                        + decimal_tuple.exponent
                    )
                    if minimum_decimal_digits > maximum_numerator_bits:
                        raise ValueError(
                            "cap numerator exceeds the parser-safety bit limit"
                        )
                else:
                    trailing_zeros = 0
                    for digit in reversed(decimal_tuple.digits):
                        if digit:
                            break
                        trailing_zeros += 1
                    uncancelled_scale = max(
                        0,
                        -decimal_tuple.exponent - trailing_zeros,
                    )
                    if uncancelled_scale >= maximum_denominator_bits:
                        raise ValueError(
                            "cap denominator exceeds the parser-safety bit limit"
                        )
            numerator, denominator = value.as_integer_ratio()
        else:
            numerator, denominator = value, 1

        if abs(numerator).bit_length() > maximum_numerator_bits:
            raise ValueError("cap numerator exceeds the parser-safety bit limit")
        if denominator.bit_length() > maximum_denominator_bits:
            raise ValueError("cap denominator exceeds the parser-safety bit limit")

        cap = cls(numerator, denominator)
        return cap.require_ranges(
            maximum_numerator_bits=maximum_numerator_bits,
            maximum_denominator_bits=maximum_denominator_bits,
            minimum_numerator=minimum_numerator,
            maximum_numerator=maximum_numerator,
            minimum_denominator=minimum_denominator,
            maximum_denominator=maximum_denominator,
            minimum_effective_cap=minimum_effective_cap,
            maximum_effective_cap=maximum_effective_cap,
            minimum_effective_cap_inclusive=minimum_effective_cap_inclusive,
            maximum_effective_cap_inclusive=maximum_effective_cap_inclusive,
        )

    def require_ranges(
        self,
        *,
        maximum_numerator_bits: int | None = None,
        maximum_denominator_bits: int | None = None,
        minimum_numerator: int | None = None,
        maximum_numerator: int | None = None,
        minimum_denominator: int | None = None,
        maximum_denominator: int | None = None,
        minimum_effective_cap: RationalCap | int | Decimal | None = None,
        maximum_effective_cap: RationalCap | int | Decimal | None = None,
        minimum_effective_cap_inclusive: bool = True,
        maximum_effective_cap_inclusive: bool = True,
    ) -> RationalCap:
        """Reject values outside exact caller-supplied structural/value ranges."""

        _validate_optional_integer_bounds(
            minimum_numerator, maximum_numerator, label="numerator"
        )
        _validate_optional_integer_bounds(
            minimum_denominator,
            maximum_denominator,
            label="denominator",
            positive=True,
        )
        if maximum_numerator_bits is not None:
            maximum_numerator_bits = _require_positive_int(
                maximum_numerator_bits, label="maximum_numerator_bits"
            )
        if maximum_denominator_bits is not None:
            maximum_denominator_bits = _require_positive_int(
                maximum_denominator_bits, label="maximum_denominator_bits"
            )
        if not isinstance(minimum_effective_cap_inclusive, bool):
            raise TypeError("minimum_effective_cap_inclusive must be a bool")
        if not isinstance(maximum_effective_cap_inclusive, bool):
            raise TypeError("maximum_effective_cap_inclusive must be a bool")

        minimum_cap = _coerce_effective_cap_bound(
            minimum_effective_cap, label="minimum_effective_cap"
        )
        maximum_cap = _coerce_effective_cap_bound(
            maximum_effective_cap, label="maximum_effective_cap"
        )
        _validate_effective_bounds(
            minimum_cap,
            maximum_cap,
            minimum_inclusive=minimum_effective_cap_inclusive,
            maximum_inclusive=maximum_effective_cap_inclusive,
        )

        if (
            maximum_numerator_bits is not None
            and abs(self.numerator).bit_length() > maximum_numerator_bits
        ):
            raise ValueError("cap numerator exceeds the caller-supplied bit limit")
        if (
            maximum_denominator_bits is not None
            and self.denominator.bit_length() > maximum_denominator_bits
        ):
            raise ValueError("cap denominator exceeds the caller-supplied bit limit")
        if minimum_numerator is not None and self.numerator < minimum_numerator:
            raise ValueError("cap numerator is below the caller-supplied minimum")
        if maximum_numerator is not None and self.numerator > maximum_numerator:
            raise ValueError("cap numerator exceeds the caller-supplied maximum")
        if minimum_denominator is not None and self.denominator < minimum_denominator:
            raise ValueError("cap denominator is below the caller-supplied minimum")
        if maximum_denominator is not None and self.denominator > maximum_denominator:
            raise ValueError("cap denominator exceeds the caller-supplied maximum")
        if minimum_cap is not None:
            minimum_comparison = _compare_rational_caps(self, minimum_cap)
            if minimum_comparison < 0 or (
                minimum_comparison == 0 and not minimum_effective_cap_inclusive
            ):
                raise ValueError("cap is below the caller-supplied effective minimum")
        if maximum_cap is not None:
            maximum_comparison = _compare_rational_caps(self, maximum_cap)
            if maximum_comparison > 0 or (
                maximum_comparison == 0 and not maximum_effective_cap_inclusive
            ):
                raise ValueError("cap exceeds the caller-supplied effective maximum")
        return self


def _coerce_effective_cap_bound(
    value: RationalCap | int | Decimal | None,
    *,
    label: str,
) -> RationalCap | None:
    if value is None:
        return None
    if isinstance(value, RationalCap):
        return value
    try:
        return RationalCap.from_value(value)
    except (TypeError, ValueError) as error:
        raise type(error)(f"{label}: {error}") from error


def _compare_rational_caps(left: RationalCap, right: RationalCap) -> int:
    left_product = left.numerator * right.denominator
    right_product = right.numerator * left.denominator
    return (left_product > right_product) - (left_product < right_product)


def _validate_effective_bounds(
    minimum_cap: RationalCap | None,
    maximum_cap: RationalCap | None,
    *,
    minimum_inclusive: bool,
    maximum_inclusive: bool,
) -> None:
    if minimum_cap is None or maximum_cap is None:
        return
    bounds_order = _compare_rational_caps(minimum_cap, maximum_cap)
    if bounds_order > 0:
        raise ValueError(
            "minimum_effective_cap must not exceed maximum_effective_cap"
        )
    if bounds_order == 0 and not (minimum_inclusive and maximum_inclusive):
        raise ValueError("exclusive equal effective-cap bounds are empty")


@dataclass(frozen=True, slots=True)
class RtssGeneration:
    """Immutable application, session, profile, and evidence identity."""

    application_generation: int
    session_generation: int
    profile_generation: int
    profile_identity: CanonicalProfileIdentity
    source_generation: int = 0

    def __post_init__(self) -> None:
        _require_nonnegative_int(
            self.application_generation, label="application_generation"
        )
        _require_nonnegative_int(self.session_generation, label="session_generation")
        _require_nonnegative_int(self.profile_generation, label="profile_generation")
        _require_nonnegative_int(self.source_generation, label="source_generation")
        if not isinstance(self.profile_identity, CanonicalProfileIdentity):
            raise TypeError("profile_identity must be a CanonicalProfileIdentity")


@dataclass(frozen=True, slots=True)
class RtssCapabilityInfo:
    """Observed capabilities without selecting a production policy."""

    backend_generation: int
    denominator_strategies: tuple[RtssDenominatorStrategy, ...] = ()
    can_read_flags: bool = False
    can_write_flags: bool = False
    supports_exact_readback: bool = False
    minimum_numerator: int | None = None
    maximum_numerator: int | None = None
    minimum_denominator: int | None = None
    maximum_denominator: int | None = None
    maximum_numerator_bits: int | None = None
    maximum_denominator_bits: int | None = None
    minimum_effective_cap: RationalCap | int | Decimal | None = None
    maximum_effective_cap: RationalCap | int | Decimal | None = None
    minimum_effective_cap_inclusive: bool = True
    maximum_effective_cap_inclusive: bool = True
    version_label: str | None = None

    def __post_init__(self) -> None:
        _require_nonnegative_int(self.backend_generation, label="backend_generation")
        strategies = tuple(self.denominator_strategies)
        if any(
            not isinstance(strategy, RtssDenominatorStrategy)
            for strategy in strategies
        ):
            raise TypeError(
                "denominator_strategies must contain RtssDenominatorStrategy values"
            )
        if len(set(strategies)) != len(strategies):
            raise ValueError("denominator_strategies must not contain duplicates")
        if RtssDenominatorStrategy.UNRESOLVED in strategies:
            raise ValueError("UNRESOLVED is not an observed denominator capability")
        object.__setattr__(self, "denominator_strategies", strategies)

        for label in ("can_read_flags", "can_write_flags", "supports_exact_readback"):
            if not isinstance(getattr(self, label), bool):
                raise TypeError(f"{label} must be a bool")
        if self.version_label is not None and not isinstance(self.version_label, str):
            raise TypeError("version_label must be a string or None")

        _validate_optional_integer_bounds(
            self.minimum_numerator,
            self.maximum_numerator,
            label="numerator",
        )
        _validate_optional_integer_bounds(
            self.minimum_denominator,
            self.maximum_denominator,
            label="denominator",
            positive=True,
        )
        if self.maximum_numerator_bits is not None:
            _require_positive_int(
                self.maximum_numerator_bits, label="maximum_numerator_bits"
            )
        if self.maximum_denominator_bits is not None:
            _require_positive_int(
                self.maximum_denominator_bits, label="maximum_denominator_bits"
            )
        if not isinstance(self.minimum_effective_cap_inclusive, bool):
            raise TypeError("minimum_effective_cap_inclusive must be a bool")
        if not isinstance(self.maximum_effective_cap_inclusive, bool):
            raise TypeError("maximum_effective_cap_inclusive must be a bool")

        minimum_cap = _coerce_effective_cap_bound(
            self.minimum_effective_cap, label="minimum_effective_cap"
        )
        maximum_cap = _coerce_effective_cap_bound(
            self.maximum_effective_cap, label="maximum_effective_cap"
        )
        _validate_effective_bounds(
            minimum_cap,
            maximum_cap,
            minimum_inclusive=self.minimum_effective_cap_inclusive,
            maximum_inclusive=self.maximum_effective_cap_inclusive,
        )
        object.__setattr__(self, "minimum_effective_cap", minimum_cap)
        object.__setattr__(self, "maximum_effective_cap", maximum_cap)

    def validate_cap(self, cap: RationalCap) -> RationalCap:
        """Validate a cap against only the ranges supplied by this capability."""

        if not isinstance(cap, RationalCap):
            raise TypeError("cap must be a RationalCap")
        return cap.require_ranges(
            maximum_numerator_bits=self.maximum_numerator_bits,
            maximum_denominator_bits=self.maximum_denominator_bits,
            minimum_numerator=self.minimum_numerator,
            maximum_numerator=self.maximum_numerator,
            minimum_denominator=self.minimum_denominator,
            maximum_denominator=self.maximum_denominator,
            minimum_effective_cap=self.minimum_effective_cap,
            maximum_effective_cap=self.maximum_effective_cap,
            minimum_effective_cap_inclusive=self.minimum_effective_cap_inclusive,
            maximum_effective_cap_inclusive=self.maximum_effective_cap_inclusive,
        )


def _validate_sha256_digest(value: object, *, label: str) -> bytes:
    if not isinstance(value, bytes):
        raise TypeError(f"{label} must be bytes")
    if len(value) != sha256().digest_size:
        raise ValueError(f"{label} must be a complete SHA-256 digest")
    return value


def _validate_field_availability(
    availability: object,
    *,
    label: str,
) -> RtssFieldAvailability:
    if not isinstance(availability, RtssFieldAvailability):
        raise TypeError(f"{label}_availability must be an RtssFieldAvailability")
    return availability


@dataclass(frozen=True, slots=True)
class RtssReadFailureDiagnostic:
    """Typed immutable detail for one failed exact stored-field observation."""

    field: RtssStoredFieldKind
    code: str
    message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.field, RtssStoredFieldKind):
            raise TypeError("diagnostic field must be an RtssStoredFieldKind")
        _require_nonempty_string(self.code, label="diagnostic code")
        if self.message is not None:
            _require_nonempty_string(self.message, label="diagnostic message")


@dataclass(frozen=True, slots=True)
class RtssStoredFieldEvidence:
    """Availability, exact value, and typed failure detail for one stored field."""

    availability: RtssFieldAvailability
    value: int | None = None
    diagnostic: RtssReadFailureDiagnostic | None = None

    def __post_init__(self) -> None:
        availability = _validate_field_availability(
            self.availability,
            label="stored_field",
        )
        if availability is RtssFieldAvailability.AVAILABLE:
            _require_plain_int(self.value, label="stored field value")
        elif self.value is not None:
            raise ValueError(
                "unavailable stored field evidence must not contain a value"
            )
        if availability is RtssFieldAvailability.READ_FAILED:
            if not isinstance(self.diagnostic, RtssReadFailureDiagnostic):
                raise ValueError(
                    "failed stored field evidence requires a typed diagnostic"
                )
        elif self.diagnostic is not None:
            raise ValueError(
                "stored field diagnostic is only valid for READ_FAILED evidence"
            )


@dataclass(frozen=True, slots=True)
class RtssStoredCapEvidence:
    """Independent exact numerator/denominator evidence for one stored cap."""

    numerator: RtssStoredFieldEvidence
    denominator: RtssStoredFieldEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.numerator, RtssStoredFieldEvidence):
            raise TypeError("numerator must be RtssStoredFieldEvidence")
        if not isinstance(self.denominator, RtssStoredFieldEvidence):
            raise TypeError("denominator must be RtssStoredFieldEvidence")
        if (
            self.numerator.diagnostic is not None
            and self.numerator.diagnostic.field
            is not RtssStoredFieldKind.NUMERATOR
        ):
            raise ValueError(
                "numerator failure diagnostic must identify the numerator"
            )
        if (
            self.denominator.diagnostic is not None
            and self.denominator.diagnostic.field
            is not RtssStoredFieldKind.DENOMINATOR
        ):
            raise ValueError(
                "denominator failure diagnostic must identify the denominator"
            )
        if self.status is RtssStoredCapStatus.CAPTURED:
            if self.denominator.value <= 0:
                raise ValueError("stored denominator must be positive")

    @classmethod
    def available(
        cls,
        numerator: int,
        denominator: int,
    ) -> RtssStoredCapEvidence:
        """Build a complete exact stored pair without reducing its representation."""

        return cls(
            RtssStoredFieldEvidence(RtssFieldAvailability.AVAILABLE, numerator),
            RtssStoredFieldEvidence(RtssFieldAvailability.AVAILABLE, denominator),
        )

    @classmethod
    def unavailable(
        cls,
        availability: RtssFieldAvailability,
    ) -> RtssStoredCapEvidence:
        """Build one coherent non-value evidence state for both stored fields."""

        if availability is RtssFieldAvailability.AVAILABLE:
            raise ValueError("available stored evidence requires exact values")
        if availability is RtssFieldAvailability.READ_FAILED:
            return cls.read_failed(
                numerator_code="numerator_read_failed",
                denominator_code="denominator_read_failed",
            )
        return cls(
            RtssStoredFieldEvidence(availability),
            RtssStoredFieldEvidence(availability),
        )

    @property
    def availability(self) -> RtssFieldAvailability | None:
        """Return the coherent availability, or ``None`` for asymmetric evidence."""

        if self.numerator.availability is self.denominator.availability:
            return self.numerator.availability
        return None

    @classmethod
    def read_failed(
        cls,
        *,
        numerator_code: str,
        denominator_code: str,
        numerator_message: str | None = None,
        denominator_message: str | None = None,
    ) -> RtssStoredCapEvidence:
        """Build field-specific failed observations for the exact pair."""

        return cls(
            RtssStoredFieldEvidence(
                RtssFieldAvailability.READ_FAILED,
                diagnostic=RtssReadFailureDiagnostic(
                    RtssStoredFieldKind.NUMERATOR,
                    numerator_code,
                    numerator_message,
                ),
            ),
            RtssStoredFieldEvidence(
                RtssFieldAvailability.READ_FAILED,
                diagnostic=RtssReadFailureDiagnostic(
                    RtssStoredFieldKind.DENOMINATOR,
                    denominator_code,
                    denominator_message,
                ),
            ),
        )

    @property
    def status(self) -> RtssStoredCapStatus:
        pair = (
            self.numerator.availability,
            self.denominator.availability,
        )
        coherent_states = {
            (
                RtssFieldAvailability.NOT_REQUESTED,
                RtssFieldAvailability.NOT_REQUESTED,
            ): RtssStoredCapStatus.NOT_REQUESTED,
            (
                RtssFieldAvailability.AVAILABLE,
                RtssFieldAvailability.AVAILABLE,
            ): RtssStoredCapStatus.CAPTURED,
            (
                RtssFieldAvailability.READ_FAILED,
                RtssFieldAvailability.READ_FAILED,
            ): RtssStoredCapStatus.CAPTURE_FAILED,
            (
                RtssFieldAvailability.UNSUPPORTED,
                RtssFieldAvailability.UNSUPPORTED,
            ): RtssStoredCapStatus.UNSUPPORTED,
            (
                RtssFieldAvailability.VERIFIED_ABSENT,
                RtssFieldAvailability.VERIFIED_ABSENT,
            ): RtssStoredCapStatus.VERIFIED_ABSENT,
        }
        return coherent_states.get(pair, RtssStoredCapStatus.INCONSISTENT)

    @property
    def requested(self) -> bool:
        return self.status is not RtssStoredCapStatus.NOT_REQUESTED

    @property
    def supported(self) -> bool | None:
        if self.status is RtssStoredCapStatus.UNSUPPORTED:
            return False
        if self.status in {
            RtssStoredCapStatus.CAPTURED,
            RtssStoredCapStatus.CAPTURE_FAILED,
        }:
            return True
        return None

    @property
    def captured(self) -> bool:
        return self.status is RtssStoredCapStatus.CAPTURED

    @property
    def unresolved(self) -> bool:
        return self.requested and self.status not in {
            RtssStoredCapStatus.CAPTURED,
            RtssStoredCapStatus.VERIFIED_ABSENT,
        }

    def require_complete_for_mutation(self) -> None:
        """Fail closed when requested exact evidence was not captured completely."""

        if self.requested and not self.captured:
            raise ValueError(
                "requested exact stored numerator and denominator require "
                "complete pre-mutation capture"
            )

    @property
    def effective_cap(self) -> RationalCap | None:
        """Return only the mathematical value; retain this object for exactness."""

        if not self.captured:
            return None
        return RationalCap(self.numerator.value, self.denominator.value)


RTSS_STORED_CAP_NOT_REQUESTED = RtssStoredCapEvidence.unavailable(
    RtssFieldAvailability.NOT_REQUESTED
)


@dataclass(frozen=True, slots=True)
class CapturedProfileState:
    """Exact state captured before a later owned RTSS mutation."""

    generation: RtssGeneration
    backend_generation: int
    profile_existed: bool
    cap: RationalCap | None
    limiter_flags: int | None = None
    profile_revision: str | None = None
    profile_document: bytes | None = None
    owned_flag_mask: int = 0
    profile_revision_availability: RtssFieldAvailability = (
        RtssFieldAvailability.NOT_REQUESTED
    )
    profile_document_availability: RtssFieldAvailability = (
        RtssFieldAvailability.NOT_REQUESTED
    )
    profile_document_sha256: bytes | None = None
    stored_cap: RtssStoredCapEvidence = RTSS_STORED_CAP_NOT_REQUESTED

    def __post_init__(self) -> None:
        if not isinstance(self.generation, RtssGeneration):
            raise TypeError("generation must be an RtssGeneration")
        _require_nonnegative_int(self.backend_generation, label="backend_generation")
        if not isinstance(self.profile_existed, bool):
            raise TypeError("profile_existed must be a bool")
        if self.cap is not None and not isinstance(self.cap, RationalCap):
            raise TypeError("cap must be a RationalCap or None")
        if self.limiter_flags is not None:
            _require_nonnegative_int(self.limiter_flags, label="limiter_flags")
        if self.profile_revision is not None and not isinstance(
            self.profile_revision, str
        ):
            raise TypeError("profile_revision must be a string or None")
        if self.profile_document is not None and not isinstance(
            self.profile_document, bytes
        ):
            raise TypeError("profile_document must be bytes or None")
        if self.profile_document_sha256 is not None:
            _validate_sha256_digest(
                self.profile_document_sha256,
                label="profile_document_sha256",
            )
        revision_availability = _validate_field_availability(
            self.profile_revision_availability,
            label="profile_revision",
        )
        document_availability = _validate_field_availability(
            self.profile_document_availability,
            label="profile_document",
        )
        if not isinstance(self.stored_cap, RtssStoredCapEvidence):
            raise TypeError("stored_cap must be RtssStoredCapEvidence")
        owned_flag_mask = _require_nonnegative_int(
            self.owned_flag_mask, label="owned_flag_mask"
        )
        if not self.profile_existed:
            if self.generation.profile_identity.kind is ProfileKind.GLOBAL:
                raise ValueError("the Global profile must exist when captured")
            if self.cap is not None:
                raise ValueError("a nonexistent captured profile must not have a cap")
            if self.profile_revision is not None:
                raise ValueError(
                    "a nonexistent captured profile must not have a profile revision"
                )
            if self.profile_document is not None:
                raise ValueError(
                    "a nonexistent captured profile must not have a profile document"
                )
            if self.profile_document_sha256 is not None:
                raise ValueError(
                    "a nonexistent captured profile must not have a profile document hash"
                )
            if self.stored_cap.status not in {
                RtssStoredCapStatus.NOT_REQUESTED,
                RtssStoredCapStatus.VERIFIED_ABSENT,
            }:
                raise ValueError(
                    "a nonexistent captured profile requires absent or "
                    "unrequested stored-cap evidence"
                )
        elif self.cap is None:
            raise ValueError("an existing captured profile requires an exact cap")
        elif (
            self.stored_cap.status
            is RtssStoredCapStatus.VERIFIED_ABSENT
        ):
            raise ValueError(
                "an existing captured profile cannot have absent stored-cap evidence"
            )
        elif (
            self.stored_cap.status is RtssStoredCapStatus.CAPTURED
            and self.stored_cap.effective_cap != self.cap
        ):
            raise ValueError(
                "captured stored-cap evidence must equal the effective cap "
                "mathematically"
            )
        if owned_flag_mask and self.limiter_flags is None:
            raise ValueError("owned captured flags require exact limiter flags")
        if self.profile_revision is not None:
            _require_nonempty_string(
                self.profile_revision, label="profile_revision"
            )
        if revision_availability is RtssFieldAvailability.AVAILABLE:
            if not self.profile_existed or self.profile_revision is None:
                raise ValueError(
                    "available captured profile revision requires exact revision data"
                )
        elif revision_availability is RtssFieldAvailability.NOT_REQUESTED:
            if self.profile_revision is not None:
                raise ValueError(
                    "unrequested captured profile revision must not contain data"
                )
        elif revision_availability is RtssFieldAvailability.VERIFIED_ABSENT:
            if self.profile_existed or self.profile_revision is not None:
                raise ValueError(
                    "verified-absent captured profile revision requires an absent profile"
                )
        else:
            raise ValueError(
                "captured profile revision must be available, not requested, "
                "or verified absent"
            )
        document_evidence_count = sum(
            value is not None
            for value in (self.profile_document, self.profile_document_sha256)
        )
        if document_availability is RtssFieldAvailability.AVAILABLE:
            if not self.profile_existed or document_evidence_count != 1:
                raise ValueError(
                    "available captured profile document requires exactly one "
                    "complete document or SHA-256 digest"
                )
        elif document_availability is RtssFieldAvailability.NOT_REQUESTED:
            if document_evidence_count:
                raise ValueError(
                    "unrequested captured profile document must not contain evidence"
                )
        elif document_availability is RtssFieldAvailability.VERIFIED_ABSENT:
            if self.profile_existed or document_evidence_count:
                raise ValueError(
                    "verified-absent captured profile document requires an absent profile"
                )
        else:
            raise ValueError(
                "captured profile document must be available, not requested, "
                "or verified absent"
            )

    @property
    def pre_mutation_capture_admissible(self) -> bool:
        """Whether every requested exact stored field was captured conclusively."""

        return not self.stored_cap.requested or self.stored_cap.captured

    def require_pre_mutation_capture(self) -> None:
        """Reject incomplete requested exact evidence before future mutation."""

        self.stored_cap.require_complete_for_mutation()


@dataclass(frozen=True, slots=True)
class RtssApplyRequest:
    """One validated-intent request for a later RTSS transaction boundary."""

    generation: RtssGeneration
    cap: RationalCap
    denominator_strategy: RtssDenominatorStrategy
    allow_profile_creation: bool = False
    limiter_flag_mask: int = 0
    limiter_flag_values: int = 0
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.generation, RtssGeneration):
            raise TypeError("generation must be an RtssGeneration")
        if not isinstance(self.cap, RationalCap):
            raise TypeError("cap must be a RationalCap")
        if not isinstance(self.denominator_strategy, RtssDenominatorStrategy):
            raise TypeError(
                "denominator_strategy must be an RtssDenominatorStrategy"
            )
        if self.denominator_strategy is RtssDenominatorStrategy.UNRESOLVED:
            raise ValueError(
                "a mutation request requires a resolved denominator strategy"
            )
        if not isinstance(self.allow_profile_creation, bool):
            raise TypeError("allow_profile_creation must be a bool")
        if (
            self.allow_profile_creation
            and self.generation.profile_identity.kind is ProfileKind.GLOBAL
        ):
            raise ValueError("Global profile creation is not a valid mutation request")
        mask = _require_nonnegative_int(
            self.limiter_flag_mask, label="limiter_flag_mask"
        )
        values = _require_nonnegative_int(
            self.limiter_flag_values, label="limiter_flag_values"
        )
        if not mask and values:
            raise ValueError("flag mutation requires a non-empty owned mask")
        if values & ~mask:
            raise ValueError("limiter_flag_values must be contained by the owned mask")
        _require_nonempty_string(self.reason, label="reason")


@dataclass(frozen=True, slots=True)
class RtssReadback:
    """A structured read of one exact profile and its relevant global flags."""

    outcome: RtssOutcome
    generation: RtssGeneration
    profile_exists: bool
    cap: RationalCap | None
    limiter_flags: int | None = None
    profile_revision: str | None = None
    backend_generation: int | None = None
    failure_step: RtssFailureStep = RtssFailureStep.NONE
    error: str | None = None
    profile_revision_availability: RtssFieldAvailability = (
        RtssFieldAvailability.NOT_REQUESTED
    )
    profile_document_availability: RtssFieldAvailability = (
        RtssFieldAvailability.NOT_REQUESTED
    )
    profile_document: bytes | None = None
    profile_document_sha256: bytes | None = None
    stored_cap: RtssStoredCapEvidence = RTSS_STORED_CAP_NOT_REQUESTED

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, RtssOutcome):
            raise TypeError("outcome must be an RtssOutcome")
        if not isinstance(self.generation, RtssGeneration):
            raise TypeError("generation must be an RtssGeneration")
        if not isinstance(self.profile_exists, bool):
            raise TypeError("profile_exists must be a bool")
        if self.cap is not None and not isinstance(self.cap, RationalCap):
            raise TypeError("cap must be a RationalCap or None")
        if self.limiter_flags is not None:
            _require_nonnegative_int(self.limiter_flags, label="limiter_flags")
        if self.profile_revision is not None and not isinstance(
            self.profile_revision, str
        ):
            raise TypeError("profile_revision must be a string or None")
        if self.profile_document is not None and not isinstance(
            self.profile_document, bytes
        ):
            raise TypeError("profile_document must be bytes or None")
        if self.profile_document_sha256 is not None:
            _validate_sha256_digest(
                self.profile_document_sha256,
                label="profile_document_sha256",
            )
        revision_availability = _validate_field_availability(
            self.profile_revision_availability,
            label="profile_revision",
        )
        document_availability = _validate_field_availability(
            self.profile_document_availability,
            label="profile_document",
        )
        if not isinstance(self.stored_cap, RtssStoredCapEvidence):
            raise TypeError("stored_cap must be RtssStoredCapEvidence")
        if self.backend_generation is not None:
            _require_nonnegative_int(
                self.backend_generation, label="backend_generation"
            )
        if not isinstance(self.failure_step, RtssFailureStep):
            raise TypeError("failure_step must be an RtssFailureStep")
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError("error must be a string or None")
        if self.profile_revision is not None:
            _require_nonempty_string(
                self.profile_revision, label="profile_revision"
            )
        _validate_outcome_details(
            self.outcome,
            self.failure_step,
            self.error,
            label="readback",
        )
        if self.outcome not in RTSS_READBACK_OUTCOMES:
            raise ValueError("outcome is not valid for a read-only RTSS readback")
        if self.failure_step not in RTSS_READBACK_FAILURE_STEPS:
            raise ValueError(
                "failure step is not valid for a read-only RTSS readback"
            )
        permitted_steps = _READBACK_FAILURE_STEPS_BY_OUTCOME.get(self.outcome)
        if permitted_steps is None or self.failure_step not in permitted_steps:
            raise ValueError(
                "readback outcome has an incompatible read-only failure step"
            )
        if revision_availability is RtssFieldAvailability.AVAILABLE:
            if (
                self.outcome is not RtssOutcome.VERIFIED
                or not self.profile_exists
                or self.profile_revision is None
            ):
                raise ValueError(
                    "available profile revision requires verified exact revision data"
                )
        elif revision_availability is RtssFieldAvailability.NOT_REQUESTED:
            if self.profile_revision is not None:
                raise ValueError(
                    "unrequested profile revision must not contain data"
                )
        elif revision_availability is RtssFieldAvailability.VERIFIED_ABSENT:
            if (
                self.outcome is not RtssOutcome.VERIFIED
                or self.profile_exists
                or self.profile_revision is not None
            ):
                raise ValueError(
                    "verified-absent profile revision requires verified profile absence"
                )
        else:
            if (
                revision_availability is RtssFieldAvailability.UNSUPPORTED
                and self.outcome
                not in {
                    RtssOutcome.UNSUPPORTED_CAPABILITY,
                    RtssOutcome.POLICY_REQUIRED,
                }
            ):
                raise ValueError(
                    "unsupported profile revision requires an unsupported "
                    "or policy-required readback outcome"
                )
            if (
                revision_availability is RtssFieldAvailability.READ_FAILED
                and (
                    self.outcome is RtssOutcome.VERIFIED
                    or self.failure_step is not RtssFailureStep.READBACK
                )
            ):
                raise ValueError(
                    "failed profile revision read requires a readback failure"
                )
            if self.outcome is RtssOutcome.VERIFIED:
                raise ValueError(
                    "verified readback cannot mark profile revision unavailable"
                )
            if self.profile_revision is not None:
                raise ValueError(
                    "unavailable profile revision must not contain revision data"
                )

        document_evidence_count = sum(
            value is not None
            for value in (self.profile_document, self.profile_document_sha256)
        )
        if document_availability is RtssFieldAvailability.AVAILABLE:
            if (
                self.outcome is not RtssOutcome.VERIFIED
                or not self.profile_exists
                or document_evidence_count != 1
            ):
                raise ValueError(
                    "available profile document requires verified exact document "
                    "or SHA-256 evidence"
                )
        elif document_availability is RtssFieldAvailability.NOT_REQUESTED:
            if document_evidence_count:
                raise ValueError(
                    "unrequested profile document must not contain evidence"
                )
        elif document_availability is RtssFieldAvailability.VERIFIED_ABSENT:
            if (
                self.outcome is not RtssOutcome.VERIFIED
                or self.profile_exists
                or document_evidence_count
            ):
                raise ValueError(
                    "verified-absent profile document requires verified profile absence"
                )
        else:
            if (
                document_availability is RtssFieldAvailability.UNSUPPORTED
                and self.outcome
                not in {
                    RtssOutcome.UNSUPPORTED_CAPABILITY,
                    RtssOutcome.POLICY_REQUIRED,
                }
            ):
                raise ValueError(
                    "unsupported profile document requires an unsupported "
                    "or policy-required readback outcome"
                )
            if (
                document_availability is RtssFieldAvailability.READ_FAILED
                and (
                    self.outcome is RtssOutcome.VERIFIED
                    or self.failure_step is not RtssFailureStep.READBACK
                )
            ):
                raise ValueError(
                    "failed profile document read requires a readback failure"
                )
            if self.outcome is RtssOutcome.VERIFIED:
                raise ValueError(
                    "verified readback cannot mark profile document unavailable"
                )
            if document_evidence_count:
                raise ValueError(
                    "unavailable profile document must not contain document evidence"
                )
        if self.outcome is RtssOutcome.VERIFIED:
            if self.profile_exists and self.cap is None:
                raise ValueError("verified existing profile readback requires an exact cap")
            if not self.profile_exists:
                if self.cap is not None:
                    raise ValueError(
                        "verified absent profile readback must not have a cap"
                    )
                if self.profile_revision is not None:
                    raise ValueError(
                        "verified absent profile readback must not have a profile revision"
                    )
                if self.stored_cap.status not in {
                    RtssStoredCapStatus.NOT_REQUESTED,
                    RtssStoredCapStatus.VERIFIED_ABSENT,
                }:
                    raise ValueError(
                        "verified absent profile readback requires absent or "
                        "unrequested stored-cap evidence"
                    )
            elif (
                self.stored_cap.status
                is RtssStoredCapStatus.VERIFIED_ABSENT
            ):
                raise ValueError(
                    "verified existing profile readback cannot have absent "
                    "stored-cap evidence"
                )
            elif self.stored_cap.status in {
                RtssStoredCapStatus.CAPTURE_FAILED,
                RtssStoredCapStatus.UNSUPPORTED,
                RtssStoredCapStatus.INCONSISTENT,
            }:
                raise ValueError(
                    "verified readback cannot mark stored-cap evidence unavailable"
                )
            elif (
                self.stored_cap.status is RtssStoredCapStatus.CAPTURED
                and self.stored_cap.effective_cap != self.cap
            ):
                raise ValueError(
                    "stored-cap evidence must equal the readback cap mathematically"
                )
        else:
            if self.profile_exists:
                raise ValueError(
                    "non-verified readback must not assert that a profile exists"
                )
            if (
                self.cap is not None
                or self.limiter_flags is not None
                or self.profile_revision is not None
                or self.profile_document is not None
                or self.profile_document_sha256 is not None
            ):
                raise ValueError(
                    "non-verified readback must not expose unverified profile state"
                )
            if self.stored_cap.status is RtssStoredCapStatus.VERIFIED_ABSENT:
                raise ValueError(
                    "non-verified readback must not expose exact stored-cap state"
                )
            if self.stored_cap.status is RtssStoredCapStatus.CAPTURED:
                raise ValueError(
                    "non-verified readback must not expose a complete available "
                    "stored-cap pair"
                )
            stored_availabilities = {
                self.stored_cap.numerator.availability,
                self.stored_cap.denominator.availability,
            }
            if (
                RtssFieldAvailability.READ_FAILED in stored_availabilities
                and (
                    self.outcome is not RtssOutcome.FAILED
                    or self.failure_step is not RtssFailureStep.READBACK
                )
            ):
                raise ValueError(
                    "failed stored-cap read requires a readback failure"
                )
            if (
                RtssFieldAvailability.UNSUPPORTED in stored_availabilities
                and self.outcome
                not in {
                    RtssOutcome.UNSUPPORTED_CAPABILITY,
                    RtssOutcome.POLICY_REQUIRED,
                }
            ):
                raise ValueError(
                    "unsupported stored-cap evidence requires an unsupported "
                    "or policy-required outcome"
                )

    @property
    def verified(self) -> bool:
        return self.outcome is RtssOutcome.VERIFIED


def _document_evidence_matches(
    captured_state: CapturedProfileState,
    readback: RtssReadback,
) -> bool:
    if (
        captured_state.profile_document is not None
        and readback.profile_document is not None
    ):
        return captured_state.profile_document == readback.profile_document
    captured_digest = captured_state.profile_document_sha256
    if captured_digest is None and captured_state.profile_document is not None:
        captured_digest = sha256(captured_state.profile_document).digest()
    readback_digest = readback.profile_document_sha256
    if readback_digest is None and readback.profile_document is not None:
        readback_digest = sha256(readback.profile_document).digest()
    return captured_digest is not None and captured_digest == readback_digest


def _validate_exact_captured_state_readback(
    captured_state: CapturedProfileState,
    readback: RtssReadback,
    *,
    label: str,
) -> None:
    if not readback.verified:
        raise ValueError(f"{label} requires verified readback")
    if readback.generation != captured_state.generation:
        raise ValueError(f"{label} generation must match captured prior state")
    if readback.backend_generation is None:
        raise ValueError(f"{label} requires backend generation readback")
    if readback.backend_generation != captured_state.backend_generation:
        raise ValueError(f"{label} backend generation must match captured prior state")
    if readback.profile_exists != captured_state.profile_existed:
        if captured_state.profile_existed:
            raise ValueError(
                f"{label} must recreate the previously existing profile"
            )
        raise ValueError(f"{label} must remove the transaction-created profile")
    if captured_state.profile_existed and readback.cap != captured_state.cap:
        raise ValueError(f"{label} cap must match captured prior state")

    stored_status = captured_state.stored_cap.status
    if stored_status is RtssStoredCapStatus.CAPTURED:
        if readback.stored_cap.status is not RtssStoredCapStatus.CAPTURED:
            raise ValueError(
                f"{label} requires exact stored numerator and denominator readback"
            )
        if readback.stored_cap != captured_state.stored_cap:
            raise ValueError(
                f"{label} stored cap representation must match captured prior state"
            )
    elif stored_status is RtssStoredCapStatus.VERIFIED_ABSENT:
        if readback.stored_cap.status is not RtssStoredCapStatus.VERIFIED_ABSENT:
            raise ValueError(
                f"{label} requires verified-absent stored-cap evidence"
            )
    elif stored_status is not RtssStoredCapStatus.NOT_REQUESTED:
        raise ValueError(
            f"{label} cannot prove exact storage from unavailable captured evidence"
        )

    mask = captured_state.owned_flag_mask
    if mask:
        if readback.limiter_flags is None:
            raise ValueError(f"{label} requires owned flag readback")
        if (
            readback.limiter_flags & mask
            != captured_state.limiter_flags & mask
        ):
            raise ValueError(f"{label} flags must match captured prior state")

    revision_availability = captured_state.profile_revision_availability
    if revision_availability is RtssFieldAvailability.AVAILABLE:
        if (
            readback.profile_revision_availability
            is not RtssFieldAvailability.AVAILABLE
            or readback.profile_revision != captured_state.profile_revision
        ):
            raise ValueError(
                f"{label} requires matching captured profile revision evidence"
            )
    elif revision_availability is RtssFieldAvailability.VERIFIED_ABSENT:
        if (
            readback.profile_revision_availability
            is not RtssFieldAvailability.VERIFIED_ABSENT
        ):
            raise ValueError(
                f"{label} requires verified-absent profile revision evidence"
            )

    document_availability = captured_state.profile_document_availability
    if document_availability is RtssFieldAvailability.AVAILABLE:
        if (
            readback.profile_document_availability
            is not RtssFieldAvailability.AVAILABLE
        ):
            raise ValueError(
                f"{label} requires captured profile document or hash evidence"
            )
        if not _document_evidence_matches(captured_state, readback):
            raise ValueError(
                f"{label} profile document evidence must match captured prior state"
            )
    elif document_availability is RtssFieldAvailability.VERIFIED_ABSENT:
        if (
            readback.profile_document_availability
            is not RtssFieldAvailability.VERIFIED_ABSENT
        ):
            raise ValueError(
                f"{label} requires verified-absent profile document evidence"
            )


def _captured_state_readback_matches(
    captured_state: CapturedProfileState,
    readback: RtssReadback,
) -> bool:
    try:
        _validate_exact_captured_state_readback(
            captured_state,
            readback,
            label="restore verification",
        )
    except ValueError:
        return False
    return True


def _unverified_owned_flag_mask(
    captured_state: CapturedProfileState,
    readback: RtssReadback | None,
    *,
    owned_mask: int | None = None,
) -> int:
    mask = (
        captured_state.owned_flag_mask
        if owned_mask is None
        else owned_mask
    )
    if (
        mask
        and readback is not None
        and readback.verified
        and readback.backend_generation
        == captured_state.backend_generation
        and readback.limiter_flags is not None
    ):
        return (
            readback.limiter_flags ^ captured_state.limiter_flags
        ) & mask
    return mask


@dataclass(frozen=True, slots=True)
class RtssRestoreResult:
    """A structured restoration, conflict, or degraded outcome."""

    outcome: RtssOutcome
    generation: RtssGeneration
    readback: RtssReadback | None = None
    captured_state: CapturedProfileState | None = None
    failure_step: RtssFailureStep = RtssFailureStep.NONE
    error: str | None = None
    unrestored_flag_mask: int = 0
    transaction_identity: RtssTransactionIdentity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, RtssOutcome):
            raise TypeError("outcome must be an RtssOutcome")
        if not isinstance(self.generation, RtssGeneration):
            raise TypeError("generation must be an RtssGeneration")
        if self.readback is not None and not isinstance(self.readback, RtssReadback):
            raise TypeError("readback must be an RtssReadback or None")
        if self.captured_state is not None and not isinstance(
            self.captured_state, CapturedProfileState
        ):
            raise TypeError("captured_state must be a CapturedProfileState or None")
        if not isinstance(self.failure_step, RtssFailureStep):
            raise TypeError("failure_step must be an RtssFailureStep")
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError("error must be a string or None")
        unrestored_flag_mask = _require_nonnegative_int(
            self.unrestored_flag_mask,
            label="unrestored_flag_mask",
        )
        if self.transaction_identity is not None and not isinstance(
            self.transaction_identity,
            RtssTransactionIdentity,
        ):
            raise TypeError(
                "restore transaction_identity must be an RtssTransactionIdentity"
            )
        if self.readback is not None and self.readback.generation != self.generation:
            raise ValueError("restore readback generation must match result")
        if (
            self.captured_state is not None
            and self.captured_state.generation != self.generation
        ):
            raise ValueError("restore captured generation must match result")
        if (
            self.readback is not None
            and self.captured_state is not None
            and self.readback.backend_generation is not None
            and self.readback.backend_generation
            != self.captured_state.backend_generation
        ):
            raise ValueError("restore backend generation must remain consistent")
        if self.captured_state is None:
            if unrestored_flag_mask:
                raise ValueError(
                    "unrestored flag mask requires captured flag ownership"
                )
        elif unrestored_flag_mask & ~self.captured_state.owned_flag_mask:
            raise ValueError(
                "unrestored flag mask must be contained by captured flag ownership"
            )
        _validate_outcome_details(
            self.outcome,
            self.failure_step,
            self.error,
            label="restore",
        )

        disposition = _RESTORE_OUTCOME_DISPOSITIONS.get(self.outcome)
        if disposition is None:
            raise ValueError("restore outcome is not explicitly classified")
        if disposition is _RtssRestoreDisposition.INVALID:
            raise ValueError(
                f"{self.outcome.value} is not a valid restore outcome"
            )
        permitted_steps = _RESTORE_REQUIRED_FAILURE_STEPS.get(self.outcome)
        if (
            permitted_steps is not None
            and self.failure_step not in permitted_steps
        ):
            raise ValueError(
                "restore outcome has a failure step outside its defined phase"
            )

        if disposition is _RtssRestoreDisposition.VERIFIED:
            if unrestored_flag_mask:
                raise ValueError("verified restore must not report unrestored flags")
            if self.captured_state is None:
                raise ValueError("verified restore requires captured prior state")
            if self.readback is None:
                raise ValueError("verified restore requires verified readback")
            _validate_exact_captured_state_readback(
                self.captured_state,
                self.readback,
                label="verified restore",
            )
            return

        if disposition is _RtssRestoreDisposition.PRE_MUTATION_FAILED:
            if self.readback is not None:
                raise ValueError(
                    "pre-mutation failed restore must not contain readback"
                )
        elif self.captured_state is None:
            raise ValueError(
                "unresolved restore requires captured prior state"
            )

        if (
            self.captured_state is not None
            and self.readback is not None
            and _captured_state_readback_matches(
                self.captured_state,
                self.readback,
            )
        ):
            raise ValueError("exact restoration must use the verified outcome")

        if self.captured_state is not None:
            unverified_mask = _unverified_owned_flag_mask(
                self.captured_state,
                self.readback,
            )
            if unrestored_flag_mask != unverified_mask:
                raise ValueError(
                    "non-verified restore must identify every unrestored or "
                    "unverified owned flag bit"
                )

    @property
    def succeeded(self) -> bool:
        return self.outcome is RtssOutcome.VERIFIED


_PRE_MUTATION_FAILURE_STEPS = frozenset(
    {
        RtssFailureStep.VALIDATE,
        RtssFailureStep.GENERATION,
        RtssFailureStep.CAPABILITY,
        RtssFailureStep.CAPTURE,
    }
)
_POST_MUTATION_FAILURE_STEPS = frozenset(
    {
        RtssFailureStep.APPLY,
        RtssFailureStep.SAVE,
        RtssFailureStep.UPDATE,
        RtssFailureStep.READBACK,
    }
)
_APPLY_ROLLBACK_OUTCOMES = {
    RtssOutcome.VERIFIED: frozenset(),
    RtssOutcome.REJECTED_VALIDATION: frozenset(),
    RtssOutcome.STALE_GENERATION: frozenset(),
    RtssOutcome.UNSUPPORTED_CAPABILITY: frozenset(),
    RtssOutcome.POLICY_REQUIRED: frozenset(),
    RtssOutcome.CONFLICT: frozenset(),
    RtssOutcome.FAILED: frozenset(),
    RtssOutcome.FAILED_ROLLED_BACK: frozenset({RtssOutcome.VERIFIED}),
    RtssOutcome.DEGRADED: frozenset(
        {
            RtssOutcome.UNSUPPORTED_CAPABILITY,
            RtssOutcome.CONFLICT,
            RtssOutcome.FAILED,
            RtssOutcome.DEGRADED,
        }
    ),
}


def _validate_requested_flag_capture(
    request: RtssApplyRequest,
    captured_state: CapturedProfileState,
) -> None:
    requested_mask = request.limiter_flag_mask
    if requested_mask & ~captured_state.owned_flag_mask:
        raise ValueError(
            "requested limiter flag mask must be covered by captured flag ownership"
        )


@dataclass(frozen=True, slots=True)
class RtssApplyResult:
    """A structured apply outcome that can only claim verified exact readback."""

    outcome: RtssOutcome
    request: RtssApplyRequest
    readback: RtssReadback | None = None
    captured_state: CapturedProfileState | None = None
    rollback: RtssRestoreResult | None = None
    failure_step: RtssFailureStep = RtssFailureStep.NONE
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, RtssOutcome):
            raise TypeError("outcome must be an RtssOutcome")
        if not isinstance(self.request, RtssApplyRequest):
            raise TypeError("request must be an RtssApplyRequest")
        if self.readback is not None and not isinstance(self.readback, RtssReadback):
            raise TypeError("readback must be an RtssReadback or None")
        if self.captured_state is not None and not isinstance(
            self.captured_state, CapturedProfileState
        ):
            raise TypeError("captured_state must be a CapturedProfileState or None")
        if self.rollback is not None and not isinstance(
            self.rollback, RtssRestoreResult
        ):
            raise TypeError("rollback must be an RtssRestoreResult or None")
        if not isinstance(self.failure_step, RtssFailureStep):
            raise TypeError("failure_step must be an RtssFailureStep")
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError("error must be a string or None")

        request_generation = self.request.generation
        if (
            self.readback is not None
            and self.readback.generation != request_generation
        ):
            raise ValueError("apply readback generation must match request")
        if (
            self.captured_state is not None
            and self.captured_state.generation != request_generation
        ):
            raise ValueError("apply captured generation must match request")
        if (
            self.rollback is not None
            and self.rollback.generation != request_generation
        ):
            raise ValueError("apply rollback generation must match request")
        if (
            self.readback is not None
            and self.captured_state is not None
            and self.readback.backend_generation is not None
            and self.readback.backend_generation
            != self.captured_state.backend_generation
        ):
            raise ValueError("apply backend generation must remain consistent")
        permitted_rollback_outcomes = _APPLY_ROLLBACK_OUTCOMES.get(
            self.outcome
        )
        if permitted_rollback_outcomes is None:
            raise ValueError(
                "apply outcome has no explicit rollback disposition"
            )
        if self.rollback is not None:
            if self.captured_state is None:
                raise ValueError("apply rollback requires captured prior state")
            if self.rollback.captured_state != self.captured_state:
                raise ValueError(
                    "apply rollback must restore the same captured prior state"
                )
            if self.rollback.outcome not in permitted_rollback_outcomes:
                raise ValueError(
                    "rollback outcome is not valid for the apply outcome"
                )
        if self.captured_state is not None and self.request.limiter_flag_mask:
            _validate_requested_flag_capture(self.request, self.captured_state)

        _validate_outcome_details(
            self.outcome,
            self.failure_step,
            self.error,
            label="apply",
        )

        pre_capture_outcomes = {
            RtssOutcome.REJECTED_VALIDATION,
            RtssOutcome.STALE_GENERATION,
            RtssOutcome.UNSUPPORTED_CAPABILITY,
            RtssOutcome.POLICY_REQUIRED,
        }
        required_pre_capture_steps = {
            RtssOutcome.REJECTED_VALIDATION: RtssFailureStep.VALIDATE,
            RtssOutcome.STALE_GENERATION: RtssFailureStep.GENERATION,
            RtssOutcome.UNSUPPORTED_CAPABILITY: RtssFailureStep.CAPABILITY,
            RtssOutcome.POLICY_REQUIRED: RtssFailureStep.CAPABILITY,
        }
        if self.outcome in pre_capture_outcomes and any(
            item is not None
            for item in (self.readback, self.captured_state, self.rollback)
        ):
            raise ValueError(
                "pre-capture rejection must not contain transaction state"
            )
        if (
            self.outcome in required_pre_capture_steps
            and self.failure_step is not required_pre_capture_steps[self.outcome]
        ):
            raise ValueError(
                "pre-capture rejection has an outcome-inconsistent failure step"
            )
        if self.outcome is RtssOutcome.VERIFIED:
            if self.captured_state is None:
                raise ValueError("verified apply requires captured prior state")
            if self.rollback is not None:
                raise ValueError("verified apply must not contain a rollback")
            if self.readback is None or not self.readback.verified:
                raise ValueError("verified apply requires verified readback")
            if self.readback.backend_generation is None:
                raise ValueError("verified apply requires backend generation readback")
            if (
                not self.captured_state.profile_existed
                and not self.request.allow_profile_creation
            ):
                raise ValueError(
                    "verified apply cannot create a profile without permission"
                )
            if not self.readback.profile_exists:
                raise ValueError("verified apply requires the requested profile")
            if self.readback.cap != self.request.cap:
                raise ValueError("verified apply readback cap must match request")
            mask = self.request.limiter_flag_mask
            if mask:
                if self.readback.limiter_flags is None:
                    raise ValueError("verified owned flags require flag readback")
                if (
                    self.readback.limiter_flags & mask
                    != self.request.limiter_flag_values
                ):
                    raise ValueError("verified limiter flag readback must match request")
        elif self.outcome is RtssOutcome.FAILED:
            if self.failure_step in _PRE_MUTATION_FAILURE_STEPS:
                if any(
                    item is not None
                    for item in (self.readback, self.captured_state, self.rollback)
                ):
                    raise ValueError(
                        "pre-mutation failed apply must not contain transaction state"
                    )
            elif self.failure_step in _POST_MUTATION_FAILURE_STEPS:
                if self.captured_state is None or self.readback is None:
                    raise ValueError(
                        "post-mutation failed apply requires captured state and "
                        "explicit no-change readback"
                    )
                _validate_requested_flag_capture(
                    self.request,
                    self.captured_state,
                )
                _validate_exact_captured_state_readback(
                    self.captured_state,
                    self.readback,
                    label="post-mutation failed apply no-change proof",
                )
            else:
                raise ValueError(
                    "failed apply step does not define a valid mutation disposition"
                )
        elif self.outcome is RtssOutcome.FAILED_ROLLED_BACK:
            if self.failure_step not in _POST_MUTATION_FAILURE_STEPS:
                raise ValueError(
                    "rolled-back apply requires the original mutation failure step"
                )
            if self.captured_state is None:
                raise ValueError("rolled-back apply requires captured prior state")
            if self.rollback is None:
                raise ValueError("rolled-back apply requires a rollback result")
            if not self.rollback.succeeded:
                raise ValueError("rolled-back apply requires verified rollback")
        elif self.outcome is RtssOutcome.DEGRADED:
            if self.failure_step not in _POST_MUTATION_FAILURE_STEPS:
                raise ValueError(
                    "degraded apply requires the original mutation failure step"
                )
            if self.captured_state is None:
                raise ValueError("degraded apply requires captured prior state")
            if self.rollback is None:
                raise ValueError(
                    "degraded apply requires an unresolved rollback"
                )
            requested_mask = self.request.limiter_flag_mask
            expected_unrestored_mask = _unverified_owned_flag_mask(
                self.captured_state,
                self.rollback.readback,
                owned_mask=requested_mask,
            )
            reported_unrestored_mask = (
                self.rollback.unrestored_flag_mask & requested_mask
            )
            if reported_unrestored_mask != expected_unrestored_mask:
                raise ValueError(
                    "degraded apply rollback must identify every unresolved "
                    "requested owned flag bit"
                )
        elif (
            self.outcome is RtssOutcome.CONFLICT
            and self.failure_step is not RtssFailureStep.CONFLICT
        ):
            raise ValueError("apply conflict requires the conflict step")

    @property
    def succeeded(self) -> bool:
        return self.outcome is RtssOutcome.VERIFIED


@dataclass(frozen=True, slots=True)
class RtssTransactionIdentity:
    """Typed immutable identity for one deterministic transaction attempt."""

    value: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.value, label="transaction identity")


@dataclass(frozen=True, slots=True)
class RtssCapabilityEvidence:
    """Immutable capability observation tied to one transaction and capture."""

    transaction_identity: RtssTransactionIdentity
    generation: RtssGeneration
    backend_generation: int
    capability_generation: int

    def __post_init__(self) -> None:
        if not isinstance(
            self.transaction_identity,
            RtssTransactionIdentity,
        ):
            raise TypeError(
                "transaction_identity must be an RtssTransactionIdentity"
            )
        if not isinstance(self.generation, RtssGeneration):
            raise TypeError("generation must be an RtssGeneration")
        _require_nonnegative_int(
            self.backend_generation,
            label="backend_generation",
        )
        _require_nonnegative_int(
            self.capability_generation,
            label="capability_generation",
        )


@dataclass(frozen=True, slots=True)
class RtssOwnershipToken:
    """The exact captured state and capability evidence owned by one holder.

    Structural equality defines the logical token: an unchanged immutable copy
    represents the same owner. Single consumption and duplicate-release
    prevention belong to the future coordinator registry, not object identity.
    """

    transaction_identity: RtssTransactionIdentity
    captured_state: CapturedProfileState
    capability_evidence: RtssCapabilityEvidence
    holder: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.transaction_identity,
            RtssTransactionIdentity,
        ):
            raise TypeError(
                "transaction_identity must be an RtssTransactionIdentity"
            )
        if not isinstance(self.captured_state, CapturedProfileState):
            raise TypeError("captured_state must be a CapturedProfileState")
        if not isinstance(self.capability_evidence, RtssCapabilityEvidence):
            raise TypeError(
                "capability_evidence must be an RtssCapabilityEvidence"
            )
        if (
            self.capability_evidence.transaction_identity
            != self.transaction_identity
        ):
            raise ValueError(
                "ownership capability evidence must match the transaction"
            )
        if (
            self.capability_evidence.generation
            != self.captured_state.generation
        ):
            raise ValueError(
                "ownership capability evidence must match the captured generation"
            )
        if (
            self.capability_evidence.backend_generation
            != self.captured_state.backend_generation
        ):
            raise ValueError(
                "ownership capability evidence must match the captured backend epoch"
            )
        _require_nonempty_string(self.holder, label="ownership holder")

    @property
    def generation(self) -> RtssGeneration:
        return self.captured_state.generation

    @property
    def backend_generation(self) -> int:
        return self.captured_state.backend_generation

    @property
    def capability_generation(self) -> int:
        return self.capability_evidence.capability_generation


@dataclass(frozen=True, slots=True, init=False)
class RtssReadbackEvidence:
    """One readback bound to the exact transaction owner that observed it."""

    ownership: RtssOwnershipToken
    readback: RtssReadback
    capability_evidence: RtssCapabilityEvidence

    @classmethod
    def bind(
        cls,
        ownership: RtssOwnershipToken,
        readback: RtssReadback,
        *,
        capability_evidence: RtssCapabilityEvidence | None = None,
    ) -> RtssReadbackEvidence:
        """Validate complete provenance before admitting degraded read evidence."""

        if not isinstance(ownership, RtssOwnershipToken):
            raise TypeError("readback ownership must be an RtssOwnershipToken")
        if not isinstance(readback, RtssReadback):
            raise TypeError("readback must be an RtssReadback")
        if readback.generation != ownership.generation:
            raise ValueError(
                "readback evidence generation and profile must match the owner"
            )
        if readback.backend_generation is None:
            raise ValueError(
                "transaction-bound readback evidence requires a backend epoch"
            )
        if readback.backend_generation != ownership.backend_generation:
            raise ValueError(
                "readback backend evidence must match captured ownership"
            )

        if capability_evidence is None:
            capability_evidence = ownership.capability_evidence
        elif not isinstance(capability_evidence, RtssCapabilityEvidence):
            raise TypeError(
                "readback capability evidence must be an RtssCapabilityEvidence"
            )

        if capability_evidence.transaction_identity != ownership.transaction_identity:
            raise ValueError(
                "readback capability evidence must match the owner transaction"
            )
        if capability_evidence.generation != ownership.generation:
            raise ValueError(
                "readback capability evidence generation and profile must match"
            )
        if capability_evidence.backend_generation != readback.backend_generation:
            raise ValueError(
                "readback capability evidence must describe the observed backend"
            )
        if capability_evidence != ownership.capability_evidence:
            raise ValueError(
                "readback must preserve exact owner capability evidence"
            )

        evidence = object.__new__(cls)
        object.__setattr__(evidence, "ownership", ownership)
        object.__setattr__(evidence, "readback", readback)
        object.__setattr__(
            evidence,
            "capability_evidence",
            capability_evidence,
        )
        return evidence

    @property
    def transaction_identity(self) -> RtssTransactionIdentity:
        return self.ownership.transaction_identity

    @property
    def generation(self) -> RtssGeneration:
        return self.readback.generation

    @property
    def backend_generation(self) -> int:
        # bind() requires concrete backend evidence.
        return self.readback.backend_generation

    @property
    def profile_identity(self) -> CanonicalProfileIdentity:
        return self.generation.profile_identity

    @property
    def profile_kind(self) -> ProfileKind:
        return self.profile_identity.kind


@dataclass(frozen=True, slots=True, init=False)
class RtssUnresolvedFieldEvidence:
    """Derived field-specific evidence for one unresolved responsibility."""

    field: RtssOwnedField
    availability: RtssFieldAvailability
    reason: str

@dataclass(frozen=True, slots=True, init=False)
class RtssDegradedFieldAccounting:
    """A derived partition; callers cannot author structural truth directly."""

    applicable_fields: frozenset[RtssOwnedField]
    resolved_fields: frozenset[RtssOwnedField]
    unresolved_evidence: tuple[RtssUnresolvedFieldEvidence, ...]

    @property
    def unresolved_fields(self) -> frozenset[RtssOwnedField]:
        return frozenset(item.field for item in self.unresolved_evidence)


def _coerce_owned_field_set(
    values: Iterable[RtssOwnedField],
    *,
    label: str,
) -> frozenset[RtssOwnedField]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{label} must be an iterable of RtssOwnedField values")
    converted = frozenset(values)
    if any(not isinstance(value, RtssOwnedField) for value in converted):
        raise TypeError(f"{label} must contain RtssOwnedField values")
    return converted


def _captured_owned_fields(
    captured_state: CapturedProfileState,
) -> frozenset[RtssOwnedField]:
    fields: set[RtssOwnedField] = set()
    if captured_state.profile_existed:
        fields.update(
            {
                RtssOwnedField.PROFILE_EXISTENCE,
                RtssOwnedField.EFFECTIVE_CAP,
            }
        )
        # Applicability is ownership intent, not observation success. Requested
        # failed, unsupported, or asymmetric exact evidence must remain visible.
        if captured_state.stored_cap.requested:
            fields.update(
                {
                    RtssOwnedField.EXACT_STORED_NUMERATOR,
                    RtssOwnedField.EXACT_STORED_DENOMINATOR,
                }
            )
    else:
        fields.update(
            {
                RtssOwnedField.PROFILE_DELETION,
                RtssOwnedField.VERIFIED_PROFILE_ABSENCE,
            }
        )
    if (
        captured_state.profile_document_availability
        is RtssFieldAvailability.AVAILABLE
    ):
        fields.add(RtssOwnedField.PROFILE_DOCUMENT)
    if (
        captured_state.profile_revision_availability
        is RtssFieldAvailability.AVAILABLE
    ):
        fields.add(RtssOwnedField.PROFILE_REVISION)
    if captured_state.owned_flag_mask:
        fields.add(RtssOwnedField.LIMITER_FLAGS)
    return frozenset(fields)


def _resolved_captured_fields(
    captured_state: CapturedProfileState,
    readback: RtssReadback | None,
) -> frozenset[RtssOwnedField]:
    if (
        readback is None
        or not readback.verified
        or readback.generation != captured_state.generation
        or readback.backend_generation != captured_state.backend_generation
    ):
        return frozenset()

    resolved: set[RtssOwnedField] = set()
    if captured_state.profile_existed:
        if readback.profile_exists:
            resolved.add(RtssOwnedField.PROFILE_EXISTENCE)
        if readback.profile_exists and readback.cap == captured_state.cap:
            resolved.add(RtssOwnedField.EFFECTIVE_CAP)
        if (
            captured_state.stored_cap.numerator.availability
            is RtssFieldAvailability.AVAILABLE
            and readback.stored_cap.numerator.availability
            is RtssFieldAvailability.AVAILABLE
            and readback.stored_cap.numerator
            == captured_state.stored_cap.numerator
        ):
            resolved.add(RtssOwnedField.EXACT_STORED_NUMERATOR)
        if (
            captured_state.stored_cap.denominator.availability
            is RtssFieldAvailability.AVAILABLE
            and readback.stored_cap.denominator.availability
            is RtssFieldAvailability.AVAILABLE
            and readback.stored_cap.denominator
            == captured_state.stored_cap.denominator
        ):
            resolved.add(RtssOwnedField.EXACT_STORED_DENOMINATOR)
    elif not readback.profile_exists:
        resolved.update(
            {
                RtssOwnedField.PROFILE_DELETION,
                RtssOwnedField.VERIFIED_PROFILE_ABSENCE,
            }
        )

    if (
        captured_state.profile_document_availability
        is RtssFieldAvailability.AVAILABLE
        and readback.profile_document_availability
        is RtssFieldAvailability.AVAILABLE
        and _document_evidence_matches(captured_state, readback)
    ):
        resolved.add(RtssOwnedField.PROFILE_DOCUMENT)
    if (
        captured_state.profile_revision_availability
        is RtssFieldAvailability.AVAILABLE
        and readback.profile_revision_availability
        is RtssFieldAvailability.AVAILABLE
        and readback.profile_revision == captured_state.profile_revision
    ):
        resolved.add(RtssOwnedField.PROFILE_REVISION)
    if (
        captured_state.owned_flag_mask
        and readback.limiter_flags is not None
        and (
            readback.limiter_flags & captured_state.owned_flag_mask
            == captured_state.limiter_flags & captured_state.owned_flag_mask
        )
    ):
        resolved.add(RtssOwnedField.LIMITER_FLAGS)
    return frozenset(resolved)


@dataclass(frozen=True, slots=True)
class RtssDiagnostic:
    """Small immutable diagnostic whose text never determines structural truth."""

    code: str
    message: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.code, label="diagnostic code")
        if self.message is not None:
            _require_nonempty_string(self.message, label="diagnostic message")


@dataclass(frozen=True, slots=True, init=False)
class RtssOperationEvidence:
    """Factory-only save or activation result with complete provenance."""

    operation: RtssOwnedField
    ownership: RtssOwnershipToken
    readback_evidence: RtssReadbackEvidence | None
    diagnostic: RtssDiagnostic | None
    _state: RtssOperationState

    @staticmethod
    def _validate_operation(operation: RtssOwnedField) -> None:
        if operation not in {
            RtssOwnedField.SAVE,
            RtssOwnedField.ACTIVATION,
        }:
            raise ValueError(
                "operation evidence must describe save or activation"
            )

    @classmethod
    def _create(
        cls,
        operation: RtssOwnedField,
        ownership: RtssOwnershipToken,
        state: RtssOperationState,
        diagnostic: RtssDiagnostic | None,
        readback_evidence: RtssReadbackEvidence | None,
    ) -> RtssOperationEvidence:
        cls._validate_operation(operation)
        if not isinstance(ownership, RtssOwnershipToken):
            raise TypeError("operation ownership must be an RtssOwnershipToken")
        if readback_evidence is not None:
            if not isinstance(readback_evidence, RtssReadbackEvidence):
                raise TypeError(
                    "operation readback must be RtssReadbackEvidence"
                )
            if readback_evidence.ownership != ownership:
                raise ValueError(
                    "operation readback evidence must match the exact owner"
                )
        if diagnostic is not None and not isinstance(
            diagnostic,
            RtssDiagnostic,
        ):
            raise TypeError("operation diagnostic must be an RtssDiagnostic")
        if state is RtssOperationState.VERIFIED:
            if (
                readback_evidence is None
                or not readback_evidence.readback.verified
            ):
                raise ValueError(
                    "verified operation requires a verified "
                    "transaction-bound readback"
                )
            if diagnostic is not None:
                raise ValueError(
                    "verified operation must not contain a diagnostic"
                )
        elif state is RtssOperationState.UNCERTAIN:
            if diagnostic is None:
                raise ValueError(
                    "uncertain operation requires a diagnostic"
                )
            if (
                readback_evidence is not None
                and readback_evidence.readback.verified
            ):
                raise ValueError(
                    "verified readback cannot be attached to uncertain "
                    "operation evidence"
                )
        else:
            raise ValueError(
                "operation evidence must be verified or uncertain"
            )

        evidence = object.__new__(cls)
        object.__setattr__(evidence, "operation", operation)
        object.__setattr__(evidence, "ownership", ownership)
        object.__setattr__(
            evidence,
            "readback_evidence",
            readback_evidence,
        )
        object.__setattr__(evidence, "diagnostic", diagnostic)
        object.__setattr__(evidence, "_state", state)
        return evidence

    @classmethod
    def verified(
        cls,
        operation: RtssOwnedField,
        ownership: RtssOwnershipToken,
        readback_evidence: RtssReadbackEvidence,
    ) -> RtssOperationEvidence:
        """Derive verified success only from a matching verified observation."""

        if not isinstance(readback_evidence, RtssReadbackEvidence):
            raise TypeError(
                "verified operation requires RtssReadbackEvidence"
            )
        if not readback_evidence.readback.verified:
            raise ValueError(
                "verified operation requires a verified transaction-bound readback"
            )
        return cls._create(
            operation,
            ownership,
            RtssOperationState.VERIFIED,
            None,
            readback_evidence,
        )

    @classmethod
    def uncertain(
        cls,
        operation: RtssOwnedField,
        ownership: RtssOwnershipToken,
        diagnostic: RtssDiagnostic,
        *,
        readback_evidence: RtssReadbackEvidence | None = None,
    ) -> RtssOperationEvidence:
        """Record uncertainty without accepting Boolean success or raw epochs."""

        if not isinstance(diagnostic, RtssDiagnostic):
            raise TypeError(
                "uncertain operation requires an RtssDiagnostic"
            )
        if (
            readback_evidence is not None
            and readback_evidence.readback.verified
        ):
            raise ValueError(
                "verified readback cannot be attached to uncertain operation evidence"
            )
        return cls._create(
            operation,
            ownership,
            RtssOperationState.UNCERTAIN,
            diagnostic,
            readback_evidence,
        )

    @property
    def state(self) -> RtssOperationState:
        return self._state

    @property
    def transaction_identity(self) -> RtssTransactionIdentity:
        return self.ownership.transaction_identity

    @property
    def generation(self) -> RtssGeneration:
        return self.ownership.generation

    @property
    def backend_generation(self) -> int:
        if self.readback_evidence is not None:
            return self.readback_evidence.backend_generation
        return self.ownership.backend_generation

    @property
    def capability_evidence(self) -> RtssCapabilityEvidence:
        if self.readback_evidence is not None:
            return self.readback_evidence.capability_evidence
        return self.ownership.capability_evidence


def _captured_conflict_value(
    captured_state: CapturedProfileState,
    owned_field: RtssOwnedField,
) -> str | bytes | int | RationalCap:
    if owned_field is RtssOwnedField.EXACT_STORED_NUMERATOR:
        evidence = captured_state.stored_cap.numerator
        if evidence.availability is not RtssFieldAvailability.AVAILABLE:
            raise ValueError(
                "numerator conflict requires exact captured numerator evidence"
            )
        return evidence.value
    if owned_field is RtssOwnedField.EXACT_STORED_DENOMINATOR:
        evidence = captured_state.stored_cap.denominator
        if evidence.availability is not RtssFieldAvailability.AVAILABLE:
            raise ValueError(
                "denominator conflict requires exact captured denominator evidence"
            )
        return evidence.value
    if owned_field is RtssOwnedField.EFFECTIVE_CAP:
        if captured_state.cap is None:
            raise ValueError("effective-cap conflict requires an exact captured cap")
        return captured_state.cap
    if owned_field is RtssOwnedField.PROFILE_DOCUMENT:
        if captured_state.profile_document is not None:
            return captured_state.profile_document
        if captured_state.profile_document_sha256 is not None:
            return captured_state.profile_document_sha256
        raise ValueError(
            "document conflict requires exact captured document evidence"
        )
    if owned_field is RtssOwnedField.PROFILE_REVISION:
        if captured_state.profile_revision is None:
            raise ValueError(
                "revision conflict requires exact captured revision evidence"
            )
        return captured_state.profile_revision
    if owned_field is RtssOwnedField.LIMITER_FLAGS:
        if captured_state.limiter_flags is None:
            raise ValueError(
                "flag conflict requires exact captured flag evidence"
            )
        return captured_state.limiter_flags
    raise ValueError("conflict evidence must identify a comparable owned field")


def _observed_conflict_value(
    captured_state: CapturedProfileState,
    readback: RtssReadback,
    owned_field: RtssOwnedField,
) -> str | bytes | int | RationalCap:
    if owned_field is RtssOwnedField.EXACT_STORED_NUMERATOR:
        evidence = readback.stored_cap.numerator
        if evidence.availability is not RtssFieldAvailability.AVAILABLE:
            raise ValueError(
                "numerator conflict requires an available field observation"
            )
        return evidence.value
    if owned_field is RtssOwnedField.EXACT_STORED_DENOMINATOR:
        evidence = readback.stored_cap.denominator
        if evidence.availability is not RtssFieldAvailability.AVAILABLE:
            raise ValueError(
                "denominator conflict requires an available field observation"
            )
        return evidence.value
    if owned_field is RtssOwnedField.EFFECTIVE_CAP:
        if not readback.verified or readback.cap is None:
            raise ValueError(
                "effective-cap conflict requires verified exact readback"
            )
        return readback.cap
    if owned_field is RtssOwnedField.PROFILE_DOCUMENT:
        if captured_state.profile_document is not None:
            if readback.profile_document is None:
                raise ValueError(
                    "document conflict requires the captured evidence form"
                )
            return readback.profile_document
        if readback.profile_document_sha256 is None:
            raise ValueError(
                "document conflict requires the captured digest evidence form"
            )
        return readback.profile_document_sha256
    if owned_field is RtssOwnedField.PROFILE_REVISION:
        if (
            not readback.verified
            or readback.profile_revision_availability
            is not RtssFieldAvailability.AVAILABLE
            or readback.profile_revision is None
        ):
            raise ValueError(
                "revision conflict requires verified exact revision readback"
            )
        return readback.profile_revision
    if owned_field is RtssOwnedField.LIMITER_FLAGS:
        if not readback.verified or readback.limiter_flags is None:
            raise ValueError("flag conflict requires verified exact flag readback")
        return readback.limiter_flags
    raise ValueError("conflict evidence must identify a comparable owned field")


@dataclass(frozen=True, slots=True, init=False)
class RtssConflictEvidence:
    """Factory-only conflict derived from the owner and one bound observation."""

    field: RtssOwnedField
    ownership: RtssOwnershipToken
    readback_evidence: RtssReadbackEvidence
    captured_value: str | bytes | int | RationalCap
    observed_value: str | bytes | int | RationalCap

    @classmethod
    def from_readback(
        cls,
        field: RtssOwnedField,
        ownership: RtssOwnershipToken,
        readback_evidence: RtssReadbackEvidence,
    ) -> RtssConflictEvidence:
        """Derive both conflict values and all provenance from exact evidence."""

        if not isinstance(ownership, RtssOwnershipToken):
            raise TypeError("conflict ownership must be an RtssOwnershipToken")
        if not isinstance(readback_evidence, RtssReadbackEvidence):
            raise TypeError(
                "conflict observation must be RtssReadbackEvidence"
            )
        if readback_evidence.ownership != ownership:
            raise ValueError(
                "conflict observation must match the exact transaction owner"
            )
        if field not in _captured_owned_fields(ownership.captured_state):
            raise ValueError(
                "conflict field must be requested, applicable, and owned"
            )

        captured_value = _captured_conflict_value(
            ownership.captured_state,
            field,
        )
        observed_value = _observed_conflict_value(
            ownership.captured_state,
            readback_evidence.readback,
            field,
        )
        if type(captured_value) is not type(observed_value):
            raise TypeError(
                "conflict values must have the same concrete evidence type"
            )
        if captured_value == observed_value:
            raise ValueError(
                "conflict evidence requires a differing field observation"
            )

        evidence = object.__new__(cls)
        object.__setattr__(evidence, "field", field)
        object.__setattr__(evidence, "ownership", ownership)
        object.__setattr__(
            evidence,
            "readback_evidence",
            readback_evidence,
        )
        object.__setattr__(evidence, "captured_value", captured_value)
        object.__setattr__(evidence, "observed_value", observed_value)
        return evidence

    @property
    def transaction_identity(self) -> RtssTransactionIdentity:
        return self.ownership.transaction_identity

    @property
    def generation(self) -> RtssGeneration:
        return self.ownership.generation

    @property
    def backend_generation(self) -> int:
        return self.readback_evidence.backend_generation

    @property
    def capability_evidence(self) -> RtssCapabilityEvidence:
        return self.readback_evidence.capability_evidence


def _make_unresolved_field_evidence(
    owned_field: RtssOwnedField,
    availability: RtssFieldAvailability,
    reason: str,
) -> RtssUnresolvedFieldEvidence:
    evidence = object.__new__(RtssUnresolvedFieldEvidence)
    object.__setattr__(evidence, "field", owned_field)
    object.__setattr__(evidence, "availability", availability)
    object.__setattr__(evidence, "reason", reason)
    return evidence


def _make_degraded_accounting(
    applicable: set[RtssOwnedField],
    resolved: set[RtssOwnedField],
    unresolved: tuple[RtssUnresolvedFieldEvidence, ...],
) -> RtssDegradedFieldAccounting:
    accounting = object.__new__(RtssDegradedFieldAccounting)
    object.__setattr__(accounting, "applicable_fields", frozenset(applicable))
    object.__setattr__(accounting, "resolved_fields", frozenset(resolved))
    object.__setattr__(accounting, "unresolved_evidence", unresolved)
    return accounting


def _availability_from_readback_outcome(
    readback: RtssReadback,
) -> RtssFieldAvailability:
    if readback.outcome is RtssOutcome.UNSUPPORTED_CAPABILITY:
        return RtssFieldAvailability.UNSUPPORTED
    if readback.outcome is RtssOutcome.FAILED:
        return RtssFieldAvailability.READ_FAILED
    return RtssFieldAvailability.NOT_REQUESTED


def _unresolved_availability(
    owned_field: RtssOwnedField,
    captured_state: CapturedProfileState,
    readback_evidence: RtssReadbackEvidence | None,
    save_evidence: RtssOperationEvidence | None,
    activation_evidence: RtssOperationEvidence | None,
) -> RtssFieldAvailability:
    readback = (
        None if readback_evidence is None else readback_evidence.readback
    )
    if owned_field is RtssOwnedField.EXACT_STORED_NUMERATOR:
        source = (
            readback.stored_cap.numerator
            if readback is not None
            else captured_state.stored_cap.numerator
        )
        return source.availability
    if owned_field is RtssOwnedField.EXACT_STORED_DENOMINATOR:
        source = (
            readback.stored_cap.denominator
            if readback is not None
            else captured_state.stored_cap.denominator
        )
        return source.availability
    if owned_field is RtssOwnedField.PROFILE_DOCUMENT:
        if readback is not None:
            return readback.profile_document_availability
        return captured_state.profile_document_availability
    if owned_field is RtssOwnedField.PROFILE_REVISION:
        if readback is not None:
            return readback.profile_revision_availability
        return captured_state.profile_revision_availability
    if owned_field in {
        RtssOwnedField.PROFILE_DELETION,
        RtssOwnedField.VERIFIED_PROFILE_ABSENCE,
    }:
        if readback is not None and readback.verified and not readback.profile_exists:
            return RtssFieldAvailability.VERIFIED_ABSENT
        if readback is not None:
            return _availability_from_readback_outcome(readback)
        return RtssFieldAvailability.VERIFIED_ABSENT
    if owned_field is RtssOwnedField.SAVE:
        if save_evidence is None:
            return RtssFieldAvailability.NOT_REQUESTED
        return RtssFieldAvailability.READ_FAILED
    if owned_field is RtssOwnedField.ACTIVATION:
        if activation_evidence is None:
            return RtssFieldAvailability.NOT_REQUESTED
        return RtssFieldAvailability.READ_FAILED
    if owned_field is RtssOwnedField.BACKEND_EPOCH:
        return RtssFieldAvailability.AVAILABLE
    if readback is not None and not readback.verified:
        return _availability_from_readback_outcome(readback)
    return RtssFieldAvailability.AVAILABLE


def _derived_degraded_classification(
    accounting: RtssDegradedFieldAccounting,
    *,
    readback_evidence: RtssReadbackEvidence | None,
    conflict_evidence: RtssConflictEvidence | None,
) -> RtssDegradedClassification:
    if conflict_evidence is not None:
        return RtssDegradedClassification.EXTERNAL_CONFLICT
    availabilities = {
        evidence.availability for evidence in accounting.unresolved_evidence
    }
    if RtssFieldAvailability.READ_FAILED in availabilities:
        return RtssDegradedClassification.READ_FAILURE
    if availabilities & {
        RtssFieldAvailability.NOT_REQUESTED,
        RtssFieldAvailability.UNSUPPORTED,
    }:
        return RtssDegradedClassification.EVIDENCE_UNAVAILABLE
    readback = (
        None if readback_evidence is None else readback_evidence.readback
    )
    if readback is not None and readback.verified and accounting.resolved_fields:
        return RtssDegradedClassification.PARTIAL_RESTORATION
    return RtssDegradedClassification.UNRESOLVED_MUTATION


@dataclass(frozen=True, slots=True)
class RtssDegradedState:
    """Complete immutable attribution and unresolved ownership evidence."""

    request: RtssApplyRequest
    current_owner: RtssOwnershipToken
    reason: str
    readback_evidence: RtssReadbackEvidence | None = None
    save_evidence: RtssOperationEvidence | None = None
    activation_evidence: RtssOperationEvidence | None = None
    conflict_evidence: RtssConflictEvidence | None = None
    accounting: RtssDegradedFieldAccounting = field(init=False)
    classification: RtssDegradedClassification = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.request, RtssApplyRequest):
            raise TypeError("request must be an RtssApplyRequest")
        if not isinstance(self.current_owner, RtssOwnershipToken):
            raise TypeError("current_owner must be an RtssOwnershipToken")
        if self.readback_evidence is not None and not isinstance(
            self.readback_evidence,
            RtssReadbackEvidence,
        ):
            raise TypeError(
                "readback_evidence must be RtssReadbackEvidence or None"
            )
        _require_nonempty_string(self.reason, label="degraded reason")

        generation = self.request.generation
        if self.current_owner.generation != generation:
            raise ValueError(
                "degraded owner generation and profile must match the request"
            )
        if (
            self.readback_evidence is not None
            and self.readback_evidence.ownership != self.current_owner
        ):
            raise ValueError(
                "degraded readback evidence must match the exact transaction owner"
            )

        for operation, expected_field in (
            (self.save_evidence, RtssOwnedField.SAVE),
            (self.activation_evidence, RtssOwnedField.ACTIVATION),
        ):
            if operation is None:
                continue
            if not isinstance(operation, RtssOperationEvidence):
                raise TypeError(
                    "save and activation evidence must be RtssOperationEvidence"
                )
            if operation.operation is not expected_field:
                raise ValueError("operation evidence is assigned to the wrong field")
            if operation.ownership != self.current_owner:
                raise ValueError(
                    "operation evidence must match the exact transaction owner"
                )
            if (
                operation.readback_evidence is not None
                and operation.readback_evidence != self.readback_evidence
            ):
                raise ValueError(
                    "operation and degraded readback observations must be coherent"
                )
        if self.conflict_evidence is not None:
            if not isinstance(self.conflict_evidence, RtssConflictEvidence):
                raise TypeError(
                    "conflict_evidence must be an RtssConflictEvidence or None"
                )
            if self.conflict_evidence.ownership != self.current_owner:
                raise ValueError(
                    "conflict evidence must match the exact transaction owner"
                )
            if (
                self.conflict_evidence.readback_evidence
                != self.readback_evidence
            ):
                raise ValueError(
                    "conflict and degraded readback observations must be identical"
                )

        captured_state = self.current_owner.captured_state
        readback = (
            None
            if self.readback_evidence is None
            else self.readback_evidence.readback
        )
        applicable = set(_captured_owned_fields(captured_state))
        resolved = set(
            _resolved_captured_fields(captured_state, readback)
        )
        applicable.add(RtssOwnedField.BACKEND_EPOCH)
        observed_backend_generations = [captured_state.backend_generation]
        if self.readback_evidence is not None:
            observed_backend_generations.append(
                self.readback_evidence.backend_generation
            )
        if any(
            observed < captured_state.backend_generation
            for observed in observed_backend_generations
        ):
            raise ValueError(
                "degraded backend evidence cannot predate captured ownership"
            )
        latest_backend_generation = max(observed_backend_generations)
        if latest_backend_generation == captured_state.backend_generation:
            resolved.add(RtssOwnedField.BACKEND_EPOCH)
        applicable.add(RtssOwnedField.RETAINED_OWNERSHIP)
        resolved.add(RtssOwnedField.RETAINED_OWNERSHIP)

        for operation, owned_field in (
            (self.save_evidence, RtssOwnedField.SAVE),
            (self.activation_evidence, RtssOwnedField.ACTIVATION),
        ):
            if operation is None or operation.state is RtssOperationState.NOT_APPLICABLE:
                continue
            applicable.add(owned_field)
            if operation.state is RtssOperationState.VERIFIED:
                resolved.add(owned_field)

        unresolved_fields = applicable - resolved
        if not unresolved_fields:
            raise ValueError(
                "degraded state requires at least one unresolved applicable field"
            )
        unresolved_evidence = tuple(
            _make_unresolved_field_evidence(
                owned_field,
                _unresolved_availability(
                    owned_field,
                    captured_state,
                    self.readback_evidence,
                    self.save_evidence,
                    self.activation_evidence,
                ),
                f"{owned_field.value} remains unresolved",
            )
            for owned_field in sorted(
                unresolved_fields,
                key=lambda item: item.value,
            )
        )
        accounting = _make_degraded_accounting(
            applicable,
            resolved,
            unresolved_evidence,
        )
        object.__setattr__(self, "accounting", accounting)
        classification = _derived_degraded_classification(
            accounting,
            readback_evidence=self.readback_evidence,
            conflict_evidence=self.conflict_evidence,
        )
        object.__setattr__(self, "classification", classification)

    @property
    def transaction_identity(self) -> RtssTransactionIdentity:
        return self.current_owner.transaction_identity

    @property
    def captured_state(self) -> CapturedProfileState:
        return self.current_owner.captured_state

    @property
    def evidence_generation(self) -> RtssGeneration:
        if self.readback_evidence is not None:
            return self.readback_evidence.generation
        return self.current_owner.generation

    @property
    def readback(self) -> RtssReadback | None:
        if self.readback_evidence is None:
            return None
        return self.readback_evidence.readback

    @property
    def ownership_retained(self) -> bool:
        return True

    @property
    def latest_backend_generation(self) -> int:
        observations = [self.captured_state.backend_generation]
        if self.readback_evidence is not None:
            observations.append(self.readback_evidence.backend_generation)
        return max(observations)

    @property
    def capability_generation(self) -> int:
        return self.latest_capability_evidence.capability_generation

    @property
    def latest_capability_evidence(self) -> RtssCapabilityEvidence:
        if self.readback_evidence is not None:
            return self.readback_evidence.capability_evidence
        return self.current_owner.capability_evidence

    @property
    def save_state(self) -> RtssOperationState:
        if self.save_evidence is None:
            return RtssOperationState.NOT_APPLICABLE
        return self.save_evidence.state

    @property
    def activation_state(self) -> RtssOperationState:
        if self.activation_evidence is None:
            return RtssOperationState.NOT_APPLICABLE
        return self.activation_evidence.state

    @property
    def profile_identity(self) -> CanonicalProfileIdentity:
        return self.request.generation.profile_identity

    @property
    def profile_kind(self) -> ProfileKind:
        return self.profile_identity.kind

    @property
    def requested_generation(self) -> RtssGeneration:
        return self.request.generation

    @property
    def captured_generation(self) -> RtssGeneration:
        return self.captured_state.generation

    @property
    def readback_generation(self) -> RtssGeneration | None:
        if self.readback_evidence is None:
            return None
        return self.readback_evidence.generation


@dataclass(frozen=True, slots=True)
class RtssDegradedHandoff:
    """A complete degraded-state offer to one defined recipient."""

    degraded_state: RtssDegradedState
    recipient: str

    def __post_init__(self) -> None:
        if not isinstance(self.degraded_state, RtssDegradedState):
            raise TypeError("degraded_state must be an RtssDegradedState")
        _require_nonempty_string(self.recipient, label="handoff recipient")


@dataclass(frozen=True, slots=True)
class RtssHandoffResult:
    """Explicit accepted or rejected responsibility transfer."""

    handoff: RtssDegradedHandoff
    decision: RtssHandoffDecision
    reason: str
    recipient_ownership: RtssOwnershipToken | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.handoff, RtssDegradedHandoff):
            raise TypeError("handoff must be an RtssDegradedHandoff")
        if not isinstance(self.decision, RtssHandoffDecision):
            raise TypeError("decision must be an RtssHandoffDecision")
        _require_nonempty_string(self.reason, label="handoff decision reason")

        if self.decision is RtssHandoffDecision.REJECTED:
            if self.recipient_ownership is not None:
                raise ValueError(
                    "rejected handoff must not assign recipient ownership"
                )
            return

        if not isinstance(self.recipient_ownership, RtssOwnershipToken):
            raise ValueError(
                "accepted handoff requires explicit recipient ownership"
            )
        state = self.handoff.degraded_state
        recipient = self.recipient_ownership
        if recipient.holder != self.handoff.recipient:
            raise ValueError(
                "accepted handoff owner must be the defined recipient"
            )
        if recipient.transaction_identity != state.transaction_identity:
            raise ValueError(
                "accepted handoff transaction identity must match"
            )
        if recipient.generation != state.request.generation:
            raise ValueError(
                "accepted handoff profile and generation must match"
            )
        if recipient.captured_state != state.captured_state:
            raise ValueError(
                "accepted handoff must preserve the exact owned capture"
            )
        if (
            recipient.capability_evidence
            != state.current_owner.capability_evidence
        ):
            raise ValueError(
                "accepted handoff must preserve immutable capability evidence"
            )

    @property
    def ownership_released(self) -> bool:
        return self.decision is RtssHandoffDecision.ACCEPTED


@dataclass(frozen=True, slots=True)
class RtssExactRestorationProof:
    """One coherent proof joining an owner, its capture, capability, and restore."""

    ownership: RtssOwnershipToken
    restoration: RtssRestoreResult

    def __post_init__(self) -> None:
        if not isinstance(self.ownership, RtssOwnershipToken):
            raise TypeError("proof ownership must be an RtssOwnershipToken")
        if not isinstance(self.restoration, RtssRestoreResult):
            raise TypeError("proof restoration must be an RtssRestoreResult")
        if not self.restoration.succeeded:
            raise ValueError("restoration proof requires a verified restore result")
        if (
            self.restoration.transaction_identity
            != self.ownership.transaction_identity
        ):
            raise ValueError(
                "restoration proof transaction identity must match the exact owner"
            )
        if self.restoration.captured_state != self.ownership.captured_state:
            raise ValueError(
                "restoration proof must restore the owner's exact captured state"
            )
        if self.restoration.generation != self.ownership.generation:
            raise ValueError(
                "restoration proof generation must match the exact owner"
            )
        if (
            self.restoration.readback is None
            or self.restoration.readback.generation
            != self.ownership.generation
        ):
            raise ValueError(
                "restoration proof requires owner-matching verified readback"
            )
        if (
            self.restoration.readback.backend_generation
            != self.ownership.backend_generation
        ):
            raise ValueError(
                "restoration proof backend epoch must match the exact owner"
            )
        capability = self.ownership.capability_evidence
        if capability.transaction_identity != self.ownership.transaction_identity:
            raise ValueError(
                "restoration proof capability evidence must match the owner transaction"
            )
        if capability.generation != self.ownership.generation:
            raise ValueError(
                "restoration proof capability evidence must match the owner generation"
            )
        if capability.backend_generation != self.ownership.backend_generation:
            raise ValueError(
                "restoration proof capability evidence must match the owner backend"
            )


@dataclass(frozen=True, slots=True)
class RtssOwnershipRelease:
    """Proof that ownership was released through one admitted invariant."""

    ownership: RtssOwnershipToken
    reason: RtssOwnershipReleaseReason
    restoration_proof: RtssExactRestorationProof | None = None
    handoff: RtssHandoffResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.ownership, RtssOwnershipToken):
            raise TypeError("ownership must be an RtssOwnershipToken")
        if not isinstance(self.reason, RtssOwnershipReleaseReason):
            raise TypeError("reason must be an RtssOwnershipReleaseReason")

        if self.reason is RtssOwnershipReleaseReason.EXACT_RESTORATION:
            if self.handoff is not None:
                raise ValueError(
                    "exact-restoration release must not contain a handoff"
                )
            if not isinstance(
                self.restoration_proof,
                RtssExactRestorationProof,
            ):
                raise ValueError(
                    "exact-restoration release requires one immutable proof"
                )
            if self.restoration_proof.ownership != self.ownership:
                raise ValueError(
                    "restoration proof belongs to a different ownership token"
                )
            return

        if self.restoration_proof is not None:
            raise ValueError(
                "accepted-handoff release must not contain restoration proof"
            )
        if not isinstance(self.handoff, RtssHandoffResult):
            raise ValueError(
                "accepted-handoff release requires a handoff result"
            )
        if not self.handoff.ownership_released:
            raise ValueError(
                "rejected handoff cannot release ownership"
            )
        if (
            self.handoff.handoff.degraded_state.current_owner
            != self.ownership
        ):
            raise ValueError(
                "handoff release must match the retained current owner"
            )

    @property
    def restoration(self) -> RtssRestoreResult | None:
        """Compatibility read access without a second caller-supplied proof path."""

        if self.restoration_proof is None:
            return None
        return self.restoration_proof.restoration
