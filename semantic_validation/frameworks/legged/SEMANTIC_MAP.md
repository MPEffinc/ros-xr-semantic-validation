# Legged semantic map

| Axis | Publicly auditable result |
| --- | --- |
| I1 / T1 | hand telemetry is `GATED` at `hand.isTracked`; raw status/update flags are not placed in emitted landmark/point-cloud payload. |
| I2 / T2 | the inspected hand publisher uses right hand as source; native source transition behavior is not run. |
| I3 / T3 | inspected `HandPub` headers set frame ID but not source timestamp; source-time lineage is not established. |
| I4 / T4 | ROS connection reconnect exists, but no session/generation binding to a control consumer was found. |
| I5 / T5/T6 | no linked control-consumer recovery contract was found. |

This is a partial telemetry map, not an included end-to-end robot-control semantic finding.
