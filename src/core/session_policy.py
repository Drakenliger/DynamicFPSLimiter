"""Pure admission policy for session-bound app work."""


def session_is_current(captured_session, session_number, running, *, allow_stopped=False):
    return captured_session == session_number and (running or allow_stopped)
