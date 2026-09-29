# Protocol — NOT FROZEN

No formal experiment protocol was frozen, because the PHASE 3 gate (`../hypotheses/GO_NO_GO.md`) was not
met: no real limited-authority boundary that can change recorded demonstration meaning was found.

For completeness, the minimal design that *would* be needed if a future audit finds such a boundary is
recorded here as a non-binding sketch (not a frozen protocol, no outcome has been observed):

| Arm | Content |
|---|---|
| B0 | unmodified upstream recording path |
| B1 | existing quality control: schema/count checks, measured per-stream timestamps and age limits, pause/validity flags, episode checks |
| B2 | B1 + raw input log (e.g. IsaacTeleop MCAP) bound to the episode, content-hash manifest at recording time, command-vs-next-state consistency, state replay (Isaac Lab `replay_demos --validate_states`) |
| Conditions | normal; normal control lag (negative control, must not be flagged); pause/reset; tracking loss; stale camera; limited-writer change at the real boundary |

No harness, baseline code or results exist in `baselines/`, `harness/` or `tests/`.
