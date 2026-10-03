# Run state: unattended round 2026-10-03 (M39 slowdown/stop, M12, matrix)

This file is the progress log of the approved unattended round, not research context.

| Item | Value |
|---|---|
| Start | 2026-10-03 14:36 KST; base commit 6ce9112 (ff from d6c78f3) |
| Budget | ≤ 12 h active; ≤ 150 new formal trials; pre-flight/probe counted separately |
| Trial ledger | 1A: 30 done · 1C: 36 done · 1B-V action: 6 done · M12: 72 running (16:05) · follow-up: ≤ 6 (total planned 144/150) |
| Probe ledger | P01–P07 instrumentation probes (7 runs, 14:40–14:47); 1C pre-flight PF1–PF3 (3 runs, 15:17–15:20); M12 pre-flight PF1–PF4 (4 runs, 16:00–16:04) |
| Research resources created | M39_decel/build_ws (instrumented Servo overlay, ignored); per-trial containers `--rm` only; no images created |

## Steps

| Step | State | Freeze SHA | Raw location | Next action |
|---|---|---|---|---|
| 1A slowdown measurement | done (R12) | e3091fd (results 26ddc16) | experiments/M39_decel/raw (137 MB, 822 files) | — |
| 1B JTC stop methods review | done | f3b26bb (results d9770a9) | experiments/M39_stop/raw/action | — |
| 1C stop pilot | done (R12) | f3b26bb (results d9770a9) | experiments/M39_stop/raw (141 MB) | — |
| 2 M12 | formal running | 7388f4d | experiments/M12_stamp/raw | analyze → R13 |
| 3 follow-up / M7–M9 audit | A02 draft committed (d9770a9) | — | — | follow-up choice after M12 |

## Log
- 14:36 ff to 6ce9112, clean.
- 14:40–14:47 probes; 14:48–15:16 1A formal; 15:17–15:20 1C pre-flight; 15:21 1C formal started.
- 15:21–15:58 1C + action formal; 16:00–16:04 M12 pre-flight; 16:05 M12 formal started (freeze 7388f4d).
- 16:15 incident: frozen M12 run_m12.py was edited by mistake (one dict entry) while the formal run was in progress; reverted within minutes. The running process had loaded the file at start (no effect on trials); sha256 re-verified against FREEZE_SHA256.txt (all code files OK); follow-up uses a separate copy run_m12_followup.py.
