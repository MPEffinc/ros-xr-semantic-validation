# Spes semantic map

| Invariant / transition | Native/raw observation | Canonical mapping | Publisher/server treatment | Boundary |
| --- | --- | --- | --- | --- |
| I1 / T1 | WebXR `getPose` is transform-or-null; packet has no tracking field | `AMBIGUOUS` for generic degradation | non-null pose serializes; null controller can fall back to viewer | E1; historical raw sideband remains separate |
| I2 / T2 | right input source and viewer fallback exist | `IMPLEMENTATION_INFERRED` | packet omits source identity | E1/E2 |
| I3 / T3 | frame time is not in `state` | `DIRECT` packet omission | server has no source age/sequence gate | E1/E2 |
| I4 / T4 | WSS lifecycle observable server-side | `IMPLEMENTATION_INFERRED` | control anchors are not generation-bound | E2 only |
| I5 / T5/T6 | explicit `move` exists; browser session has end handler | `IMPLEMENTATION_INFERRED` | `move=false` clears anchors but tracking/session invalidation is not a server field | E2 only |

`emulatedPosition` is not treated as a universal WebXR field. It is raw prior-capture evidence,
not an upstream packet field and not a replay input.
