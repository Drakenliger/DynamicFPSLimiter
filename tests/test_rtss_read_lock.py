"""C5 regression tests: RTSSController.get_profile_property RLock protection.

Proves get_profile_property holds _profile_lock from LoadProfile through
GetProfileProperty, preventing concurrent acquiring threads during both DLL
callbacks and properly releasing the lock on success and failure return paths.
"""
import threading
from core.rtss_functions import RTSSController


def test_get_profile_property_holds_profile_lock_during_dll_callbacks():
    ctrl = object.__new__(RTSSController)
    ctrl._profile_lock = threading.RLock()

    load_called = threading.Event()
    continue_load = threading.Event()
    get_called = threading.Event()
    continue_get = threading.Event()

    def mock_load_profile(name):
        load_called.set()
        assert continue_load.wait(timeout=5.0) is True

    def mock_get_profile_property(prop, ptr, size):
        get_called.set()
        assert continue_get.wait(timeout=5.0) is True
        return True

    ctrl.LoadProfile = mock_load_profile
    ctrl.GetProfileProperty = mock_get_profile_property

    getter_errors = []

    def getter_worker():
        try:
            res = ctrl.get_profile_property("Global", "FramerateLimit")
            assert res is not None
        except Exception as e:
            getter_errors.append(e)

    thread = threading.Thread(target=getter_worker)
    thread.start()

    # 1. Wait until getter thread enters LoadProfile callback
    assert load_called.wait(timeout=5.0) is True

    # 2. Attempt non-blocking acquire during LoadProfile execution
    acquired_during_load = ctrl._profile_lock.acquire(blocking=False)
    if acquired_during_load:
        ctrl._profile_lock.release()

    continue_load.set()

    # 3. Wait until getter thread enters GetProfileProperty callback
    assert get_called.wait(timeout=5.0) is True

    # 4. Attempt non-blocking acquire during GetProfileProperty execution
    acquired_during_get = ctrl._profile_lock.acquire(blocking=False)
    if acquired_during_get:
        ctrl._profile_lock.release()

    continue_get.set()

    thread.join(timeout=5.0)
    assert not thread.is_alive()
    assert getter_errors == []

    # 5. Assert lock was held during both DLL callbacks
    assert acquired_during_load is False
    assert acquired_during_get is False

    # 6. Assert lock is properly released after method completes
    acquired_after = ctrl._profile_lock.acquire(blocking=False)
    assert acquired_after is True
    ctrl._profile_lock.release()


def test_get_profile_property_releases_lock_on_failure():
    ctrl = object.__new__(RTSSController)
    ctrl._profile_lock = threading.RLock()

    ctrl.LoadProfile = lambda name: None
    ctrl.GetProfileProperty = lambda prop, ptr, size: False

    res = ctrl.get_profile_property("Global", "FramerateLimit")
    assert res is None

    # Lock must be released on failure returns
    acquired = ctrl._profile_lock.acquire(blocking=False)
    assert acquired is True
    ctrl._profile_lock.release()
