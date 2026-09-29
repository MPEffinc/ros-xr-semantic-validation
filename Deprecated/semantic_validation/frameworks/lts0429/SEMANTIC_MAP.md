# LTS0429 semantic map

| Axis | Publicly auditable result |
| --- | --- |
| I1 tracking / T1 | `UNMAPPED`: APK source and any native gate are unavailable; UDP wire representation has no tracking field. |
| I2 source identity / T2 | `TRANSFORMED` only as separate left/right/head topic names; native modality/device identity is unknown. |
| I3 source time / T3 | `DROPPED` at `parse_pose`, which uses receiver `this->now()`; source timestamp is absent on wire. |
| I4 generation / T4 | `UNMAPPED`: UDP datagram protocol carries no audited session/generation field. |
| I5 re-arm / T5/T6 | `UNMAPPED`: no native source/gate is inspectable. |

These are host/wire observations, not a claim about Quest behavior or a runtime result.
