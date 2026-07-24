# Release Notes

## Unreleased

No fix has been released from the review baseline.

Current work consists only of review reconciliation, safety architecture, test
planning, and tracked project-status documentation. Planned behavior in
`DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, and `TEST_PLAN.md` is not implemented.

### Known high-priority limitations

- The normal controller decrease path can fail to step down.
- FPS, process, and sensor evidence can be stale, ambiguous, or tied to the
  wrong backend.
- LibreHardwareMonitor mode remains coupled to legacy PDH behavior.
- RTSS changes are not one serialized, verified, reversible transaction.
- Previous cap and limiter state are not captured and restored.
- Stop/start and profile transitions can leave stale worker generations active.
- Autopilot, idle, and process identity are not generation-safe.
- No automated regression suite or CI currently protects controller and
  external-state behavior.

This branch is not production-ready. It makes no compatibility claim for any
RTSS version, the RX 7900 XTX, or Lossless Scaling beyond the statically
reviewed baseline. Windows integration and physical acceptance remain required.
