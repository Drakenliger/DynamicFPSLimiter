import pytest
from core.session_policy import session_is_current


@pytest.mark.parametrize('captured,current,running,allowed,expected', [
    (1, 1, True, False, True), (1, 2, True, False, False),
    (1, 1, False, False, False), (1, 1, False, True, True),
    (1, 2, False, True, False),
])
def test_session_admission(captured, current, running, allowed, expected):
    assert session_is_current(captured, current, running, allow_stopped=allowed) is expected
