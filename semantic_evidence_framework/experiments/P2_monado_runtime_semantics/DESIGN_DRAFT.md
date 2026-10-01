# P2 (draft, not frozen) — runtime-level check of the inactive-action premise on Monado

**Why.** H-A1 (cached deadman across deactivation) rests on three facts.

| Fact | Status |
|---|---|
| (a) the spec rule `changedSinceLastSync=false` for inactive actions | SOURCE_CONFIRMED |
| (b) ALVR's edge-only forwarding | SOURCE_CONFIRMED |
| (c) a real runtime behaving per (a) when focus or input is removed | NOT_VERIFIED |

P1 assumes (c). A real OpenXR runtime installed on this host, Monado 21.0 (`monado-service`), can test
(c) without a headset, if it runs headless.

**What it would and would not show.**

- It would show Monado's behaviour only. It says nothing about Meta's Quest runtime.
- It would provide an independent runtime-side observation of action state. That makes it a
  candidate for an evidence path the app cannot rewrite, for brief §8.

## Feasibility indicators (2026-10-01, no service launched yet)

- The `monado-service` and `libopenxr_monado.so` binaries contain the strings `XRT_COMPOSITOR_NULL`,
  `null compositor`, `SIMULATED_ENABLE` and `QWERTY`.
- `monado-ctl` exposes `-f <id>` (set focused client), `-p <id>` (set primary client) and
  `-i <id>` (toggle whether the client receives input).
- OpenXR loader 1.0.20 with the runtime manifest `/usr/share/openxr/1/openxr_monado.json`.
- Missing: an OpenXR test client. There is no `pyopenxr` on the host. Options:
  - a small C client against `libopenxr-dev` (headers present);
  - a container with `pip install pyopenxr` (network required at build time).

## Planned measurement (to be frozen before running)

1. Start `monado-service` with the null compositor and a simulated controller. Start one client that
   creates a session, an action set with a boolean "deadman" action and a pose action, and polls
   `xrSyncActions` / `xrGetActionStateBoolean` / `xrLocateSpace` each frame.
2. Hold the simulated deadman true. If the simulated device cannot be scripted, use a qwerty or
   simulated driver input path. If no scriptable boolean exists, record BLOCKED_ENV and stop.
3. Toggle input with `monado-ctl -i` or move focus with `-f`. Record `isActive`, `currentState`,
   `changedSinceLastSync`, `lastChangeTime`, the session state events and the location flags across
   the transition and its reversal.
4. **Oracle for (c).** While inactive: `isActive=false`, `changedSinceLastSync=false`. At the first
   active sync after it: `changedSinceLastSync=false`.
5. Then replay the recorded sequence through ALVR's `update_buttons` rule, which is pure logic. Show
   whether a release edge would ever be forwarded.

## Exclusion

If Monado cannot start headless on this host, or cannot be given a scriptable boolean input, P2 is
recorded as BLOCKED_ENV with the error output. P1's assumption (c) then stays NOT_VERIFIED.
