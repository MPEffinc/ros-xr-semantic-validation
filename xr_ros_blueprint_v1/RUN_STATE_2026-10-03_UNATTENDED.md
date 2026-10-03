# Run state: unattended round 2026-10-03 (M39 slowdown/stop, M12, matrix)

This file is the progress log of the approved unattended round, not research context.

| Item | Value |
|---|---|
| Start | 2026-10-03 14:36 KST; base commit 6ce9112 (ff from d6c78f3) |
| Budget | ≤ 12 h active; ≤ 150 new formal trials; pre-flight/probe counted separately |
| Trial ledger | 1A 30 · 1C 36 · 1B-V action 6 · M12 72 · follow-up 6 = **150/150** (all valid, 0 reruns) |
| Probe ledger | P01–P07 instrumentation probes (7 runs, 14:40–14:47); 1C pre-flight PF1–PF3 (3 runs, 15:17–15:20); M12 pre-flight PF1–PF4 (4 runs, 16:00–16:04) |
| Research resources created | M39_decel/build_ws (instrumented Servo overlay, ignored); per-trial containers `--rm` only; no images created |

## Steps

| Step | State | Freeze SHA | Raw location | Next action |
|---|---|---|---|---|
| 1A slowdown measurement | done (R12) | e3091fd (results 26ddc16) | experiments/M39_decel/raw (137 MB, 822 files) | — |
| 1B JTC stop methods review | done | f3b26bb (results d9770a9) | experiments/M39_stop/raw/action | — |
| 1C stop pilot | done (R12) | f3b26bb (results d9770a9) | experiments/M39_stop/raw (141 MB) | — |
| 2 M12 | done (R13) | 7388f4d (results 6afeadc) | experiments/M12_stamp/raw (265 MB incl. follow-up) | — |
| 3 follow-up / M7–M9 audit | done: R11a source-stall follow-up (6 trials) + A02 | d4b2fc0 | experiments/M12_stamp/raw/followup | — |

## Log
- 14:36 ff to 6ce9112, clean.
- 14:40–14:47 probes; 14:48–15:16 1A formal; 15:17–15:20 1C pre-flight; 15:21 1C formal started.
- 15:21–15:58 1C + action formal; 16:00–16:04 M12 pre-flight; 16:05 M12 formal started (freeze 7388f4d).
- 16:15 incident: frozen M12 run_m12.py was edited by mistake (one dict entry) while the formal run was in progress; reverted within minutes. The running process had loaded the file at start (no effect on trials); sha256 re-verified against FREEZE_SHA256.txt (all code files OK); follow-up uses a separate copy run_m12_followup.py.
- 17:01 M12 formal done (72/72); 17:07–17:13 R11a follow-up (6/6); 17:13–17:23 R12/R13, DB, STATUS, CONTEXT (final commit 509e3c7).
- Correction: commit 6afeadc message says A2 false blocks 0/4851; correct is 0/4508 (R13).
- End state: budget reached (150 trials); no containers of this round running (all `--rm`); kept local, ignored: raw dirs
  (M39_decel 137 MB, M39_stop 141 MB, M12_stamp 265 MB) and M39_decel/build_ws (instrumented Servo build, kept for
  reproduction). Same-disk copies/hash lists are not a recovery guarantee.
