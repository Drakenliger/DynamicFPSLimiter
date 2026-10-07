"""Pure admission and cap calculations for profile handoffs."""
from decimal import Decimal


def profile_transition_kind(target, profiles, current, running):
    if target not in profiles:
        return "invalid"
    if not running:
        return "load"
    return "same" if target == current else "switch"


def effective_max(limits):
    return max(Decimal(value) for value in limits)


def profile_request_current(session, revision, current_session, current_revision):
    return session == current_session and revision == current_revision
