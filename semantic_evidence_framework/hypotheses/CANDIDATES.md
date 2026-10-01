# Candidate hypotheses and go/exclude criteria

Both candidates are **HYPOTHESIS**. Neither is assumed to be a gap. If an existing feature or policy
already handles it, that result is recorded as a solved case.

## H-A — residual permission after action deactivation or interruption

*Claim to test:* in a real implementation, after the input action becomes inactive or the operator
interrupts manipulation, a previously granted permission (clutch/deadman latched, last button state
cached, last target retained) still lets motion commands reach the consumer. Alternatively, a
command or goal admitted under the old permission keeps executing.

| Stage | Proceed if | Exclude / record as solved if |
|---|---|---|
| Audit | code shows (a) the activity bit is dropped or not forwarded, or (b) button state is cached across a deactivation/disconnect, or (c) the consumer keeps the last target without a timeout | the activity bit is forwarded and checked, or a consumer timeout/zeroing already bounds it |
| Pilot | the ROS-side consumer moves after the declared interruption, beyond the policy bound, with synthetic deactivation input | the existing timeout (e.g., Servo `incoming_command_timeout`) already stops it within the bound. That is a solved case, with its latency recorded. |
| Comparison | the effect persists in at least 2 structurally different implementations, and the retrofits differ per implementation | a one-line forwarding/check fixes it in each. Solved; record the cost. |

## H-B — origin/anchor/calibration transition mixes input and applied-transform intervals

*Claim to test:* when the reference origin, an app calibration or an anchor changes, a pose sampled
before the change can be combined with the transform after it, or the reverse. The resulting command
corresponds to neither interval.

**Not** to be re-proposed: the OpenVR resume displacement (S5 #10, APPLICATION; fix = re-anchor on
engage).

| Stage | Proceed if | Exclude / record as solved if |
|---|---|---|
| Audit | code shows that the transform is read "latest" (e.g., `lookupTransform(..., TimePoint(0))`, a cached offset updated asynchronously, or no effective-time field), while the input sample carries its own time | the transform lookup uses the sample stamp, or the offset update and sample consumption are serialized, or no runtime origin change reaches the app at all |
| Pilot | an interval-mixed command (pose from t<T_change with the transform from t≥T_change) is produced and consumed, with nonzero motion beyond tolerance | the mix cannot occur, or produces sub-tolerance error. Solved / no effect. |
| Comparison | `tf2` time-correct lookup, a version/epoch on the offset, or a reset-on-change handler is needed per implementation, with repeated edits | a stamp-correct `lookupTransform` or a single epoch check fixes it |

## Events kept separate (do not merge)

E-ORIGIN, E-CALIB, E-DRIFT, E-TF-FORGE, E-DEACT, E-TRACK and E-DISC are distinct events. See
`../docs/02_REQUIREMENTS_AND_THREAT_MODEL.md` §2. E-TF-FORGE has a standard remedy (SROS2 topic
permissions) and is not a candidate.

## Expansion criteria (brief §8), evaluated only after audits and pilots

The framework is expanded only if all three conditions hold:

1. The same evidence/transition/enforcement requirement recurs across structurally different
   implementations. Forks are not counted separately.
2. The manual retrofit needs implementation-specific, repeated edits.
3. A common model plausibly gives the same guarantee with fewer edits, lower latency, or fewer false
   blocks.

"Unobservable" alone never justifies a new defense.
