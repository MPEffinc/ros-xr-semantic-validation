# D1 repetition 5 B2-native I_FULL observation-gap incident

Frozen trial `docker_d1_r05_b2_full` (schedule order 50) ran once and exited 0. The frozen analyzer classified it `INVALID_COMPARISON: FULL_PROPERTY_RECEIPT_BINDING_INCOMPLETE`; its paired source schedule and final joint-state comparison with the same-repetition B0-shim nevertheless passed. The raw `property.jsonl` has 858 oracle records; 857 join by exact monitor event ID to `monitor_output_received`, while one does not.

The single unjoined event had `sample_id=null`, `safe=true`, `selected_origin={origin: ORIGINAL_NEUTRAL, reason: stale_timeout}`. Unlike the repetition-2 B2-composed gap, its decision timestamp occurred **after** the common barrier. It is not one of the 120 sender source samples, but it is part of the frozen all-property receipt requirement. It therefore remains INVALID; it is not a B2 policy failure, a source rejection or proof of Gazebo control without checking. Do not change the frozen analyzer to exclude it after outcome, and do not pool this trial with valid replicates.

No ad hoc retry was run: the frozen 50-trial schedule assigns immutable IDs and the runner refuses an existing output directory. Any prospective retry extension would need to be registered and frozen before execution. Keep the failed trial and raw intact.
