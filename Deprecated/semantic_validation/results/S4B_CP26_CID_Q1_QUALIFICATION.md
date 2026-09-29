# CP26 Docker C-ID Q1 setup result: 20/20 qualified

The campaign was frozen at `068d23d017debd02538c77e295459dc3c311fc43`. All 20 first attempts ran once, reached the barrier and exited 0, with no retry.

**Result: CID_SETUP_COMPLETE, 20/20 MEASUREMENT_QUALIFIED.** The B0/shim pair (MISMATCH) passes at 0.046878 ms and 0.002566 rad.

- **I_FULL defenses:** these stopped after the slot-50 injection, with about 0.22 rad of excursion.
- **Original / I_NATIVE:** these reached about 0.30 rad.

Evidence is in `runs/s4b_cp26_cidq1_20260928T154636Z/`: `raw/`, `analysis/cid_setup_summary.json` and `runtime_evidence_manifest.sha256`, which verifies. These are setup cells only and carry no policy score.
