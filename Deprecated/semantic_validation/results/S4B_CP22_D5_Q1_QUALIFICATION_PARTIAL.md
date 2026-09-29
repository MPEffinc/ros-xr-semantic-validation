# CP22 Docker D5Q1 setup result: 12/14 qualified; two B3 cells crashed on a logging collision

The campaign was frozen at `8497e1aa073eb13066e4dc53756fce0c2414e5c5`, and all 14 first attempts ran once. Evidence is in `runs/s4b_cp22_d5q1_20260928T130939Z/`: `raw/`, the frozen `analysis/d5_setup_summary.json`, and `runtime_evidence_manifest.sha256`, which verifies.

## 12 MEASUREMENT_QUALIFIED

The B0/shim pair passed: 0.051625 ms and 0.004841 rad. The qualified cells were:

- B1, B2-native and B2-composed under I_FULL, with both R_EXPLICIT and R_AUTO;
- all four I_NATIVE arms.

## 2 BLOCKED_MEASUREMENT: B3 I_FULL under R_EXPLICIT and R_AUTO

Both cells exited with launch 12 before the start barrier. The cause was `TypeError: log() got multiple values for argument 'kind'`: the B3 re-arm event dict carried `kind`/`monotonic_ns` keys that collide with `trace.log()`. The collision crashed the receiver/mapper node.

The frozen setup runner did **not** apply its registered pre-barrier retries. It broke on `rc == 0`, but `run_owned.py` returns 0 even when the launch fails. This is a runner defect, and it is recorded here; it was not silently repaired.

## Integration defect in the qualified B2/B2-composed cells

The raw property logs show a second semantic defect, even in the B2 and B2-composed cells that qualified. Before any client connects, the original receiver's startup neutral carries `receiver_connection {index 0, open false}`. The oracle treated this as a disconnect, 5.05 s before the barrier. It then recovered through the idle dwell and re-armed on the first teleop edge (slot 20).

The recorded behavior was otherwise as designed:

- the moving disconnect was blocked;
- the gen-1 replay was blocked;
- the dwell restarted after the replay;
- the R_EXPLICIT re-arm happened at slot 94.

These are integration defects, not policy results. D5Q2 corrects them and requalifies only the affected cells. The D5Q1 verdicts are unchanged.
