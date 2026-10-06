import ctypes
import threading
import time
import pytest
from core.rtss_functions import RTSSController


class StubLogger:
    def add_log(self, msg):
        pass


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
        # Try acquiring lock from another thread; if lock is held, acquire(blocking=False) returns False
        acquired_by_other = []
        def _check():
            acquired = rtss_controller._profile_lock.acquire(blocking=False)
            if acquired:
                rtss_controller._profile_lock.release()
            acquired_by_other.append(acquired)

        t = threading.Thread(target=_check)
        t.start()
        t.join()
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
        t.join()
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
    reader_can_finish = threading.Event()

    def fake_load_profile(name):
        call_sequence.append(("LoadProfile", name.decode('ascii')))
        if name == b"ReaderProfile":
            load_started.set()
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
        # Wait until reader has entered LoadProfile
        load_started.wait(timeout=2.0)
        res = rtss_controller.set_profile_property("WriterProfile", "FramerateLimit", 60)
        writer_result.append(res)

    r_thread = threading.Thread(target=reader_thread)
    w_thread = threading.Thread(target=writer_thread)

    r_thread.start()
    w_thread.start()

    # Give writer time to attempt set_profile_property
    time.sleep(0.1)

    # Allow reader to finish
    reader_can_finish.set()

    r_thread.join(timeout=2.0)
    w_thread.join(timeout=2.0)

    assert not r_thread.is_alive()
    assert not w_thread.is_alive()

    # If lock is properly held across get_profile_property, sequence must be:
    # Reader LoadProfile -> Reader GetProfileProperty -> Writer LoadProfile -> Writer SetProfileProperty -> ...
    # It must NOT interleave Writer LoadProfile before Reader GetProfileProperty!
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
