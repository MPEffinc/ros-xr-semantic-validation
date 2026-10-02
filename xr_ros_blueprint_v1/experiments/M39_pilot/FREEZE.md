# M39 pilot: freeze record

This file is frozen by the commit that adds it. The commit SHA and the remote check are recorded in
`../../STATUS.md` and in the results document. **Any rule change after this commit needs a new
protocol version.**

| Item | Frozen value |
|---|---|
| Protocol | `../../reports/R03_M39_PILOT_REVISED_PROTOCOL.md` (§6 policies, §7 validity, §8 schedule, §10.4 pre-flight result) |
| Image | `f3-xrizer-bgpump:0989a7f-v3` = `sha256:eb60fb5f28049cd8f63569e4ce47e12b6a7fe296d88ed0742b9a61193556d135` (xrizer 0989a7f + extfilter + bg pump v3; Monado main 045931d; ROS Jazzy, MoveIt Servo 2.12.4, JTC 4.42.1, Gazebo) |
| ROS workspace (read-only mount) | `semantic_evidence_framework/experiments/P1_openvr_evidence/ws/install`, 228 files, manifest sha256 `a6b23931f10367c25f88d6082a3a4a7510fc9c74e14c5a3bc0cd06a18ee41973`; `ur_servo.yaml` sha256 `d352707c…`; `ros2_controllers.yaml` `dcf49c42…` |
| App | `quest_teleop.py` @170dad5, sha256 `0dba77d8…99d6` (B0 and C1 run the installed entry point; B1 runs `arms/quest_teleop_b1.py`) |
| Start configuration | q = −2.865212 −0.026290 −1.853711 −1.261592 −2.865212 −1.571593 (IK sol4); EE (0.4, 0, 0.3, euler xyz 0, 1.57, 0) |
| Axis | u = −x (`scenarios/axis_mx/*.json`, from `make_scenarios.py -x`) |
| Schedule | `schedule.csv` (45 rows, `make_schedule.py`) |
| Runner | `run_campaign.py` → `run_m39.py` → `harness/trial.sh` (one fresh container per trial; `--network none`) |
| Analysis | `analysis/analyze_m39.py` with `preflight/ref_increments.json` |
| Code hashes | `FREEZE_SHA256.txt` (every tracked file of this directory except this file) |

**Command used for the formal campaign:**

```
python3 run_campaign.py raw/formal schedule.csv scenarios/axis_mx "-2.865212 -0.02629 -1.853711 -1.261592 -2.865212 -1.571593"
```
