# A03 — Impact record: frozen `run_m12.py` edited during the R11 campaign (2026-10-03)

**Evidence.** File timestamps, the campaign log, and the code of the runner and of the trial
harness.

## Timeline (KST)

| Time | Event | Evidence |
|---|---|---|
| 16:05:27 | `run_m12.py schedule` process started (one Python process for the whole campaign) | first trial dir `raw/formal/M01_A1_INACT_CACHE_r1` created 16:05:38 |
| 16:14:57–16:15:51 | trial `M12_A2_DELAY_r1` in progress | campaign log (trial 11 logged 16:14:57, trial 12 logged 16:15:51) |
| ≈16:15:39 | **edit:** one dict entry `"SRC_STALL_LONG": "PASS"` added to `BRIDGE` in `run_m12.py`; `scenarios/SRC_STALL_LONG.json` created in the same command | mtime of the JSON file 16:15:39.46 |
| 16:15:48 | **restored** (`sed`); hashes re-verified OK | mtime of `run_m12.py` 16:15:48.48 (restore write) |
| ≈16:15:57 | the extra scenario moved to `scenarios_followup/`; the follow-up runner copy created | mtime of `run_m12_followup.py` 16:15:57 |

## Who read what during the window

- **The runner process** (`run_m12.py`) is a Python script. Python compiles the script once at
  start; `BRIDGE`, `run()` and `invalid()` are defined at import, and the script never re-reads its
  own source. **The edit could not change the running process.**
- **Child processes.** Each trial is `docker run … bash /m12/harness/trial_m12.sh` with the
  experiment directory mounted read-only. The container executes:
  - `harness/trial_m12.sh`;
  - `harness/chain_bridge.py`;
  - `harness/remote_feeder_m12.py`;
  - `arms/m12_gate.py`;
  - `arms/quest_teleop_m12.py`;
  - the frozen `M39_pilot` harness;
  - the scenario file of **its own condition** (`/m12/scenarios/<COND>.json`, passed as `SCEN`).

  It never executes `run_m12.py`. The invalid-check child runs `analysis/analyze_m12.py`, which was
  unchanged. The transiently present `scenarios/SRC_STALL_LONG.json` was not the condition of any
  trial running then (DELAY / CACHE).
- **Scenario and environment.** The bridge mode for the running trial had been passed as an
  environment variable at its own `docker run` (16:14:57), before the edit.

## Conclusion

- **No trial's executed code or inputs were affected.** This rests on the timeline and on the code
  paths above. The end-state hash equality alone would not prove it.
- **Process change from this round.** Campaigns execute an immutable snapshot extracted with
  `git archive` from the freeze commit, and its hashes are verified before every trial.
