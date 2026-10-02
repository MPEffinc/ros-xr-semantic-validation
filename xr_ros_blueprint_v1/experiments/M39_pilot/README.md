# M39 stop/resume pilot (code)

The protocol is `../../reports/R03_M39_PILOT_REVISED_PROTOCOL.md`. The freeze record is `FREEZE.md`, written at
freeze time. Raw outputs go under `raw/` and are ignored; their per-file hashes are committed with the results.

| Path | Role |
|---|---|
| `arms/quest_teleop_orig_170dad5.py` | the unmodified app, kept as the reference for the B1 diff |
| `arms/quest_teleop_b1.py` | B1, the app copy: every change is marked `B1:` |
| `arms/c1_transition.py` | C1, the ROS-side node (the app is unchanged) |
| `harness/m39_transition.py`, `harness/m39_evidence.py` | low-level code shared by B1 and C1 |
| `harness/trial.sh`, `run_m39.py`, `make_scenarios.py` | one trial per fresh container; the input scripts |
| `harness/observer.py`, `remote_feeder.py`, `setup_start.py`, `mnd_*.c`, `servo_launch.py` | measurement, input and setup |
| `preflight/` | B1-detection probe; offline IK and path check |
| `tests/` | host-only deterministic checks (fake world, recorded traces) |
| `analysis/` | the frozen analysis |
