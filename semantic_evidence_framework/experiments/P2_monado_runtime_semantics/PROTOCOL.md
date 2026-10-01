# P2 — Monado runtime check of the inactive-action premise (feasibility run, frozen 2026-10-01)

**Scope.** This test runs only Monado 21.0.0+git2905.e26a272c1 on this host, headless, with the
null compositor and the `remote` driver. It does not test Meta's Quest runtime, SteamVR or ALVR.

**Question.** When the runtime removes input from the session, while a boolean is held and is then
released during the removal, does the runtime report these, as `input.adoc` L853–866 requires?

1. While removed: `isActive=false`, `currentState=false`, `changedSinceLastSync=false`.
2. At the first sync after restore: `changedSinceLastSync=false`, even though the physical state changed.

**Setup.** `monado-ctl -i <id>` toggles whether the client receives input (variants A and B).
Variant F uses `-f` (focus) instead, if supported.

- **Deadman:** right `a/click`, Index profile.
- **Feeder:** `remote_feeder.py`.
- **Client:** `p2_client.c`.

**Variants.**

- **A:** held at 3–8 s; removed at 6 s; released at 8 s (while removed); restored at 10 s.
- **B:** held at 3–14 s; removed at 6–10 s.
- **F:** like A, with focus moved away instead of the input toggle.

**Oracle and derived consequence.**

- Replay each client log through ALVR's `update_buttons` rule: forward `currentState` only when
  `changedSinceLastSync`.
- **A**: H-A1's premise holds on Monado if no `false` is ever forwarded after the last forwarded
  `true`. In that case an edge-forwarding middleware keeps the deadman *pressed*.
- **B**: the rising edge at 3 s is forwarded once. After the restore there is no new edge.

**Exclusions.** If the client never reaches FOCUSED, or the toggle has no effect, the run is recorded
as BLOCKED/NO_EFFECT with its logs. Nothing is inferred from it.

**Runs.** 1 per variant. The runtime is deterministic with respect to this rule, so repetition adds
little. If the outcome is ambiguous, extend to 3 per variant.
