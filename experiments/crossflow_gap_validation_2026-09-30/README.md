# Cross-flow gap validation (2026-09-30)

**Hypothesis under test (to be refuted, not confirmed):** in XR–ROS teleoperation, even when every
traffic flow (XR media, XR pose/input, ROS command, ROS feedback) is individually protected with strong
existing traffic-analysis defenses, the cross-flow temporal correlation between XR and ROS flows leaks
additional task information.

The item is kept only if the strongest existing methods, applied faithfully, leave a reproducible residual
leakage whose removal needs a mechanism not in existing work. Otherwise it is killed and the work moves to
a new gap search (`docs/08_new_gap_search.md`).

## Workflow

| Stage | Output | Gate |
|---|---|---|
| 0 Asset inventory | `docs/00_asset_inventory.md` | — |
| 1 Topology + observer model | `docs/01_topology_and_threat_model.md`, `figures/topology.*`, `configs/topology.*` | GATE 1: one realistic observer sees ≥2 heterogeneous flows |
| 2 Dataset pipeline | `docs/02_dataset_pipeline.md`, `scripts/capture_*`, `manifests/dataset_manifest.csv` | real capture available? |
| 3 Unprotected leakage | `docs/03_unprotected_leakage.md` | GATE 2: combined > single, stably |
| 4 Cross-flow ablation | `docs/04_crossflow_causality_ablation.md` | relation itself carries information? |
| 5 Existing defenses | `literature/defense_baselines.md`, `docs/05_existing_defenses.md` | — |
| 6 Residual leakage | `docs/06_residual_crossflow_leakage.md` | residual after strong defenses? |
| 7 Decision | `DECISION.md`, `docs/07_*` or `docs/08_new_gap_search.md` | KEEP / REVISE / KILL |

Evidence levels (literature): A full paper read, B abstract/metadata, C README/docs, D our inference.
Data provenance: REAL (physical headset/robot), UPSTREAM (real software stack, synthetic input), SYNTHETIC.
Synthetic data is never used to decide novelty.

## Running

Scripts live in `scripts/`; each documents its command line. Raw captures stay outside Git (paths +
sha256 in `manifests/`).
