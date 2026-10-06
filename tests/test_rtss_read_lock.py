import ctypes
import threading
import pytest
from core.rtss_functions import RTSSController


class StubLogger:
    def add_log(self, msg):
        pass


class TrackingRLock:
    """Wraps an RLock to signal when a specific thread attempts to acquire the lock."""

    def __init__(self, target_thread_name, on_acquire_attempt_event):
        self._real_lock = threading.RLock()
        self.target_thread_name = target_thread_name
        self.on_acquire_attempt_event = on_acquire_attempt_event

    def acquire(self, blocking=True, timeout=-1):
        if threading.current_thread().name == self.target_thread_name:
            self.on_acquire_attempt_event.set()
        return self._real_lock.acquire(blocking=blocking, timeout=timeout)

    def release(self):
        return self._real_lock.release()

    def __enter__(self):
        if threading.current_thread().name == self.target_thread_name:
            self.on_acquire_attempt_event.set()
        return self._real_lock.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._real_lock.__exit__(exc_type, exc_val, exc_tb)


@pytest.fixture
def rtss_controller(tmp_path):
    ctrl = object.__new__(RTSSController)
    rtss_dir = tmp_path / "RTSS"
    profiles_dir = rtss_dir / "Profiles"
    profiles_dir.mkdir(parents=True)

    ctrl.rtss_install_path = str(rtss_dir)
    ctrl.rtss_path = str(rtss_dir / "RTSSHooks64.dll")
    ctrl.logger = StubLogger()
    ctrl._profile_lock = threading.RLock()
    ctrl._error_handler = None
    return ctrl


def test_get_profile_property_holds_lock_during_execution(rtss_controller):
    """Verify that _profile_lock is held throughout get_profile_property."""
    lock_held_in_load = False
    lock_held_in_get = False

    def fake_load_profile(name):
        nonlocal lock_held_in_load
        acquired_by_other = []

        def _check():
            acquired = rtss_controller._profile_lock.acquire(blocking=False)
            if acquired:
                rtss_controller._profile_lock.release()
            acquired_by_other.append(acquired)

        t = threading.Thread(target=_check)
        t.start()
        t.join(timeout=2.0)
        lock_held_in_load = not acquired_by_other[0]

    def fake_get_profile_property(prop_name, buf_ptr, size):
        nonlocal lock_held_in_get
        acquired_by_other = []

        def _check():
            acquired = rtss_controller._profile_lock.acquire(blocking=False)
            if acquired:
                rtss_controller._profile_lock.release()
            acquired_by_other.append(acquired)

        t = threading.Thread(target=_check)
        t.start()
        t.join(timeout=2.0)
        lock_held_in_get = not acquired_by_other[0]
        return True

    rtss_controller.LoadProfile = fake_load_profile
    rtss_controller.GetProfileProperty = fake_get_profile_property

    rtss_controller.get_profile_property("Global", "FramerateLimit", 4)

    assert lock_held_in_load, "Profile lock was not held during LoadProfile in get_profile_property"
    assert lock_held_in_get, "Profile lock was not held during GetProfileProperty in get_profile_property"


def test_get_profile_property_prevents_interleaving_with_writer(rtss_controller):
    """Verify concurrent writer cannot interleave LoadProfile/SetProfileProperty while reader is reading."""
    call_sequence = []
    load_started = threading.Event()
    writer_attempted_acquire = threading.Event()
    reader_can_finish = threading.Event()

    rtss_controller._profile_lock = TrackingRLock(
        target_thread_name="WriterThread",
        on_acquire_attempt_event=writer_attempted_acquire
    )

    def fake_load_profile(name):
        call_sequence.append(("LoadProfile", name.decode('ascii')))
        if name == b"ReaderProfile":
            load_started.set()
            # Wait until writer attempts acquiring lock while reader holds it
            writer_attempted_acquire.wait(timeout=2.0)
            # Pause reader inside LoadProfile
            reader_can_finish.wait(timeout=2.0)

    def fake_get_profile_property(prop_name, buf_ptr, size):
        call_sequence.append(("GetProfileProperty", prop_name.decode('ascii')))
        return True

    def fake_set_profile_property(prop_name, buf_ptr, size):
        call_sequence.append(("SetProfileProperty", prop_name.decode('ascii')))
        return True

    def fake_save_profile(name):
        call_sequence.append(("SaveProfile", name.decode('ascii')))

    def fake_update_profiles():
        call_sequence.append(("UpdateProfiles",))

    rtss_controller.LoadProfile = fake_load_profile
    rtss_controller.GetProfileProperty = fake_get_profile_property
    rtss_controller.SetProfileProperty = fake_set_profile_property
    rtss_controller.SaveProfile = fake_save_profile
    rtss_controller.UpdateProfiles = fake_update_profiles

    reader_result = []

    def reader_thread():
        res = rtss_controller.get_profile_property("ReaderProfile", "FramerateLimit", 4)
        reader_result.append(res)

    writer_result = []

    def writer_thread():
        load_started.wait(timeout=2.0)
        res = rtss_controller.set_profile_property("WriterProfile", "FramerateLimit", 60)
        writer_result.append(res)

    r_thread = threading.Thread(target=reader_thread, name="ReaderThread")
    w_thread = threading.Thread(target=writer_thread, name="WriterThread")

    try:
        r_thread.start()
        w_thread.start()

        # Wait until writer has attempted acquire while reader is paused in LoadProfile
        assert writer_attempted_acquire.wait(timeout=2.0), "Writer did not attempt to acquire lock"

        # Allow reader to finish
        reader_can_finish.set()

    finally:
        reader_can_finish.set()
        r_thread.join(timeout=2.0)
        w_thread.join(timeout=2.0)

    assert not r_thread.is_alive(), "Reader thread failed to exit"
    assert not w_thread.is_alive(), "Writer thread failed to exit"

    reader_get_idx = -1
    writer_load_idx = -1
    for idx, item in enumerate(call_sequence):
        if item == ("GetProfileProperty", "FramerateLimit") and reader_get_idx == -1:
            reader_get_idx = idx
        if item == ("LoadProfile", "WriterProfile") and writer_load_idx == -1:
            writer_load_idx = idx

    assert reader_get_idx != -1, f"Reader GetProfileProperty was not called. Calls: {call_sequence}"
    assert writer_load_idx != -1, f"Writer LoadProfile was not called. Calls: {call_sequence}"
    assert reader_get_idx < writer_load_idx, (
        f"Writer interleaved before reader finished! Call sequence: {call_sequence}"
    )


def test_unlocked_baseline_fails_interleaving_test(rtss_controller):
    """Verify that an unlocked get_profile_property fails interleaving assertion under same sync."""
    call_sequence = []
    load_started = threading.Event()
    writer_attempted_acquire = threading.Event()
    reader_can_finish = threading.Event()

    rtss_controller._profile_lock = TrackingRLock(
        target_thread_name="WriterThread",
        on_acquire_attempt_event=writer_attempted_acquire
    )

    # Unlocked get_profile_property implementation
    def unlocked_get_profile_property(profile_name, property_name, size=4):
        rtss_controller.LoadProfile(profile_name.encode('ascii'))
        buf = (ctypes.c_byte * size)()
        success = rtss_controller.GetProfileProperty(property_name.encode('ascii'), ctypes.byref(buf), size)
        if not success:
            return None
        return bytes(buf)

    rtss_controller.get_profile_property = unlocked_get_profile_property

    def fake_load_profile(name):
        call_sequence.append(("LoadProfile", name.decode('ascii')))
        if name == b"ReaderProfile":
            load_started.set()
            # Wait for writer to execute its set_profile_property (which acquires _profile_lock)
            writer_attempted_acquire.wait(timeout=2.0)
            reader_can_finish.wait(timeout=2.0)

    def fake_get_profile_property(prop_name, buf_ptr, size):
        call_sequence.append(("GetProfileProperty", prop_name.decode('ascii')))
        return True

    def fake_set_profile_property(prop_name, buf_ptr, size):
        call_sequence.append(("SetProfileProperty", prop_name.decode('ascii')))
        return True

    def fake_save_profile(name):
        call_sequence.append(("SaveProfile", name.decode('ascii')))

    def fake_update_profiles():
        call_sequence.append(("UpdateProfiles",))

    rtss_controller.LoadProfile = fake_load_profile
    rtss_controller.GetProfileProperty = fake_get_profile_property
    rtss_controller.SetProfileProperty = fake_set_profile_property
    rtss_controller.SaveProfile = fake_save_profile
    rtss_controller.UpdateProfiles = fake_update_profiles

    def reader_thread():
        rtss_controller.get_profile_property("ReaderProfile", "FramerateLimit", 4)

    def writer_thread():
        load_started.wait(timeout=2.0)
        rtss_controller.set_profile_property("WriterProfile", "FramerateLimit", 60)

    r_thread = threading.Thread(target=reader_thread, name="ReaderThread")
    w_thread = threading.Thread(target=writer_thread, name="WriterThread")

    try:
        r_thread.start()
        w_thread.start()

        assert writer_attempted_acquire.wait(timeout=2.0), "Writer did not attempt acquire"
        # Delay reader finishing so writer can acquire lock and interleave LoadProfile
        reader_can_finish.set()

    finally:
        reader_can_finish.set()
        r_thread.join(timeout=2.0)
        w_thread.join(timeout=2.0)

    assert not r_thread.is_alive()
    assert not w_thread.is_alive()

    reader_get_idx = -1
    writer_load_idx = -1
    for idx, item in enumerate(call_sequence):
        if item == ("GetProfileProperty", "FramerateLimit") and reader_get_idx == -1:
            reader_get_idx = idx
        if item == ("LoadProfile", "WriterProfile") and writer_load_idx == -1:
            writer_load_idx = idx

    # Unlocked baseline must interleave writer before reader GetProfileProperty
    assert writer_load_idx < reader_get_idx, "Unlocked baseline did not reproduce interleaving defect"
