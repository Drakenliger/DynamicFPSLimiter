# Dynamic FPS Limiter

## App and scope

DFL is a Windows Python desktop app: DearPyGui 2.0.0 UI, RTSS DLL/profile/shared-memory interfaces, PDH GPU counters and LibreHardwareMonitor through pythonnet. Read the task brief; use its worktree, branch and head. Authorization lives in that brief. Keep changes scoped; unrelated refactors, dependencies, CI/settings changes and external actions require authorization.

## Find relevant code

Start with the task's entry points: [app/session orchestration](src/core/app.py), [autopilot](src/core/autopilot.py), [GUI queue](src/core/gui_queue.py), [idle timer](src/core/idle_timer.py), [RTSS profiles](src/core/rtss_functions.py), [PDH monitor](src/core/gpu_monitor.py), [LHM lifecycle](src/core/librehardwaremonitor.py). Profile loading lives in [ConfigManager](src/core/config_manager.py); live FPS reads in [RTSSInterface](src/core/rtss_interface.py).

## Contracts to check

- Background GUI work goes through the app's queue; the render-context owner drains it. Submission defers execution; draining executes on its caller. Preserve ordering and error reporting. Direct-call fallbacks in helpers do not authorize background DPG calls in the app.
- Trace profile-name consumers across app, autopilot and configuration. Preserve stored names, exact-match priority and intended case-insensitive fallback; check lookup, foreground comparisons and Global switching together. Existing consumers are not uniformly case-insensitive.
- Preserve ctypes argument/return widths and handle lifetime at Windows boundaries; distinguish Win32 BOOL from DLL-specific contracts. Idle subtraction uses unsigned 32-bit wrap even with GetTickCount64.
- Preserve session/profile-revision admission under the session lock, Stop/restart invalidation and Exit restoration. Check paused native work and retired workers, not only sequential callbacks. Preserve PDH handle serialization and LHM lifecycle.
- RTSS limiter-disabled bit is literal `4`; enable/disable must be idempotent and preserve unrelated bits. Preserve profile read/write serialization, encoding, unrelated sections, flush/fsync/replace atomicity and refresh behavior. Do not infer live DLL correctness from stubs.

## Test seams and limits

Use existing environment and [fixtures](tests/conftest.py). FakeDPG records calls/threads but accepts unmodeled APIs; rtss_stub bypasses DLL loading; fake_lhm replaces .NET hardware. They cannot prove rendering, ABI marshalling or hardware behavior. The [win32 marker](pytest.ini) alone does not skip; explicit requires_win32/skip conditions do.

Relevant checks: [GUI routing](tests/test_threadsafe_gui_routing.py), [profile cases](tests/test_autopilot_case.py), [idle ABI/wrap](tests/test_idle_timer.py), [limiter bits](tests/test_rtss_limiter_flags.py), [atomic writes](tests/test_rtss_atomic.py), [write admission](tests/test_start_stop_write_admission.py), [profile handoff](tests/test_app_profile.py), [exit](tests/test_exit_restore.py), [PDH handles](tests/test_gpu_monitor_handles.py), [LHM lifecycle](tests/test_lhm_lifecycle.py).

## Validation

Run the brief's focused command using the existing interpreter. Local Linux tests require:

```bash
systemd-run --user --scope -p MemoryMax=8G -p MemorySwapMax=0 timeout 600 python -m pytest -q <brief-selected-tests>
```

If the user bus is denied, stop; never run uncapped. Full Linux baseline has platform collection errors: report actual failures separately from portable passes. Full [Windows CI](.github/workflows/windows-tests.yml) tests Python 3.12/3.13; main builds the executable on 3.12. See [build instructions](src/BUILD.md) and Afrim's [runtime acceptance](docs/windows_acceptance.md); CI does not prove RTSS/hardware acceptance.

## Delivery and review

Report scoped diff, exact head, commands/results and limitations. Independently check and obtain cross-company review of the exact head; after changes, checks/review must cover the new head. Allow one authorized fix round.

Review in the context of the whole program, not just the diff. For any changed comparison, lookup or contract, find every other place that relies on the same values and check they agree with the change.

Return two lists: verified defects (file/line, failing scenario, evidence); unverified suspicions (concern, verification needed). The coordinator checks suspicions. Claim only demonstrated behavior.
