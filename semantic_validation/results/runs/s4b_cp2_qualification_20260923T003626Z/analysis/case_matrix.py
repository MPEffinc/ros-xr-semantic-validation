"""Protocol-preserving per-case readiness inventory; no experiment scoring."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMON = "identical fixture; fresh Gazebo initial pose; full graph/recorder ACK; same boot monotonic <1ms; five reps per baseline/regime; B0-shim equivalence"
LINEAGE = "source ID/generation/native state -> original publication -> exact Servo callback; controller output parent and joint consequence separately"
CONTROL = "B0,B1,B2-native,B2-composed,B3; I_NATIVE/I_FULL equal state; official monitor oracle/envelope; positive control"
ROWS = []


def add(stack, case, state, stop, missing, verdict="BLOCKED", note=""):
    obs = ("receiver/mapper/bridge + Servo twist callback + Float64MultiArray + /joint_states"
           if stack == "Docker" else
           "production pose + Servo pose callback + JointTrajectory/controller_state + /joint_states")
    ROWS.append(dict(stack=stack, case_id=case, required_source_state=state,
                     required_lineage=LINEAGE, required_servo_controller_observation=obs,
                     required_stop_rearm=stop, required_clock_start_barrier=COMMON,
                     currently_confirmed="CP1 B0/shim positive-control pairs PASS; official ROSMonitoring runtime qualification PASS; CP2 Docker B0/Servo-observer pair PASS and 847 unique callback joins" if stack == "Docker" else
                     "CP1 timer-aligned B0/shim pair PASS; CP2 overlay 450 callback joins but both B0/overlay timing pairs INVALID; official ROSMonitoring qualification PASS; CP1 fast-hold stops, re-reference moves 0.201172 rad",
                     missing_required=missing, readiness=verdict, reason=note or "Full B0-B3 comparison preconditions not qualified"))


base = "B1/B2/B3 equal-information code/property/envelope not frozen; all-participant ACK and clock not qualified; source-to-Servo output parent unknown"
add("Docker", "D0", "no active source/control", "none beyond idle-safe baseline", base,
    note="Idle diagnostic feasible on original path, but formal four-baseline comparison unavailable")
add("Docker", "D1", "wire tracked=true, teleop=true, generation/current source time", "positive-control path; no fault rearm", base,
    note="B0 Gazebo positive control exists; B1/B2/B3 positive controls and overhead remain unqualified")
add("Docker", "D2", "same pose/teleop; only tracked=false for 1s after motion", "neutralize moving arm <=300ms command/<=1s settled; R_EXPLICIT", base+"; invalid-state stop adapter per arm not qualified")
add("Docker", "D3", "last valid source ID, no bytes for 1s", "250ms silence trigger; neutralize and settle", base+"; same watchdog across B1/B2/B3 missing")
add("Docker", "D4", "old/fresh source time offsets 0,.05,.15,.35,.75,1.0s; +1s future; F100/F250/F500", "block stale/future during active control; no reference-zero shortcut", base+"; clock-mapped atomic source metadata and all profiles missing")
add("Docker", "D4-L", "fresh source then FIFO post-gate delays 0,.05,.15,.35,.75s; all freshness profiles", "stop stale commands at consumer, distinguish B1 placement", base+"; delay injector and consumer-age check missing")
add("Docker", "D5", "connection generation, old-generation sample after reconnect", "R_EXPLICIT and R_AUTO; safe new reference and resume", base+"; full generation/recovery and stop/rearm contract missing")
add("Docker", "D6", "valid→invalid→valid held→release/press; current generation", "both recovery policies; no reference-only displacement", base+"; full recovery and stop/rearm contract missing")
add("OpenVR", "W0", "no production grip/pose", "none beyond idle-safe baseline", base,
    note="Idle diagnostic feasible on original path, not formal four-baseline comparison")
add("OpenVR", "W1", "connected=true, valid=true, result=200, grip=true", "positive-control path; no fault rearm", base+"; Jazzy Servo callback overlay equivalence invalid (>5 ms source scheduling)",
    note="B0 Gazebo positive control exists; full-information baselines unavailable")
add("OpenVR", "W2", "same W1 pose/index, only eTrackingResult=201", "reject new commands and neutralize while moving", base+"; Jazzy callback overlay equivalence invalid and composed stop path missing")
add("OpenVR", "W3", "same W1 pose/index, only bPoseIsValid=false", "block/neutralize; no false positive from no-command case", base+"; source-ID association for rejected samples and B2/B3 integration missing")
add("OpenVR", "W4", "valid ramp→invalid→valid held→release/press/new reference", "R_EXPLICIT/R_AUTO and jump-free reanchor", base+"; CP1 re-reference moved 0.201172 rad (full stop/rearm invalid)", verdict="BLOCKED")
add("OpenVR", "W5", "same W4 timing, disconnect/connection generation", "both recovery policies and jump-free reanchor", base+"; full stop/rearm and generation transport missing")
for stack in ("Docker", "OpenVR"):
    add(stack, "C-ID", "I_FULL missing/duplicate/mismatched ID and old generation", "reject/neutralize before actuation", base+"; atomic envelope and adversarial binding fixtures absent")
    add(stack, "C-MON", "B2 oracle absent/disconnect/hang; matched B1/B3 failure", "B2-native versus composed health stop; shared watchdog", base+"; complete health-to-original-path integration absent")

assert len(ROWS) == 18
fields = list(ROWS[0])
with (ROOT / "analysis" / "case_readiness.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fields)
    writer.writeheader()
    writer.writerows(ROWS)
(ROOT / "analysis" / "case_readiness.json").write_text(json.dumps(ROWS, indent=2) + "\n")
print(f"{len(ROWS)} case rows; READY={sum(r['readiness']=='READY' for r in ROWS)}")
