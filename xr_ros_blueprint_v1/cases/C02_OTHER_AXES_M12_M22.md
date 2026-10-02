# C02 — Representative candidates from the other two axes (review, 2026-10-03)

**Purpose.** Compare one candidate per axis with M39 before choosing the first experiment. M39 is
not fixed in advance. No experiment was run.

## B. Time · provenance · bypass axis: representative **M12** (stale content with a fresh stamp)

**Why M12 and not M17/M18/M19/M20/M40.**

- M12 is the premise under every freshness, interval and order check in this repository. F2 shows
  that age, interval and order checks are only as good as the stamp's meaning, and F2's timestamp
  review shows that no audited real app meets that meaning unmodified.
- M2 (the frozen focus-loss stream) is an instance of M12.
- The other cases are narrower:
  - M17/M18 need an S2 trust path that is not built;
  - M19 is a known SROS2/OS mediation test;
  - M20/M40 reuse F2's evidence-delay data.

| Item | Content | Level |
|---|---|---|
| Protected condition | A command is executed only if the input it derives from is no older than A ms at the consumer (S_end), in a declared clock domain | policy, not yet chosen per task |
| Existing solutions | (1) Stamp at the source with the sample time (OpenXR `XrTime` → `XR_KHR_convert_timespec_time`, which Monado main offers) and never restamp. (2) Consumer age check (S5 D4: solved with I_FULL). (3) Monotonic stamp or sequence for duplicate/order (F2 ORD). (4) tf2 stamped lookup (M7). | SOURCE / PRIOR_INTERNAL |
| Existing solution that does **not** cover it | ROS 2 **Lifespan** QoS measures *publish → reception* (ros2_documentation jazzy, *About QoS Settings*, Lifespan definition). A cached value republished with a fresh publish time passes it. | SOURCE (doc) |
| Related upstream state | Nav2 issue #6320 (open since 2026-08-06): no standard mechanism to detect stale transforms. That is a different stack, so the issue is not evidence about Servo or XR mappers (U48). | SOURCE |
| What remains after the fixes | (a) **Sample time ≠ evidence of freshness for inferred poses.** OpenXR returns a valid-but-untracked pose *for the requested time* (`spaces.adoc` L833–856), so a sample-time stamp on an inferred or last-known pose looks fresh. The tracked bit or `lastChangeTime` is also needed. (b) **Button values:** a cached deadman (K6) has no sample time of its own unless the app uses `lastChangeTime`. (c) **Clock domains:** headset clock vs host (PickNik R0) needs a stated sync bound. (d) **S2:** a stamp from a compromised app proves nothing (I05 R3). | INFER from SOURCE |
| Experiment feasibility | Feasible on the F3 stack: the UR5e app on patched xrizer + Monado. It would need a **modified app copy** that stamps the sample time (a per-app fix arm). | environment available |
| Equipment | existing containers only; no GPU or headset change | — |
| Expected information | It would quantify whether the strongest per-app stamping fix closes M12 for an honest app on a real path, and where (a)/(b) remain. **Likely outcome: solved by known fixes, plus a documented residual (a)/(b).** Low expected novelty, moderate matrix value. | INFER |

## C. Screen · approval · execution axis: representative **M22** (the target seen is not the target executed)

**Why M22 and not M23/M25/M26.**

- M22 is the honest-app baseline for the whole axis. If an honest app's scene-version check already
  closes it, M23 (UI deception) and M25 (coordinated FDI) are about trust in the displayed or
  reported state, not about linkage.
- M26 has no task definition yet.

| Item | Content | Level |
|---|---|---|
| Protected condition | A goal created by selecting an object or point in the displayed scene is executed only if the target still has the identity/pose it had when it was **shown** | policy; needs a target-selection task |
| Existing solutions | (1) Scene/object version in the goal, with an optimistic check at execution (a general concurrency technique; no XR→ROS-specific source read: INFER). (2) Predictive and delay-compensated display (L27 survey; the 2026 review notes that model mismatch and update transients dominate in delay-tolerant local rendering; search excerpt). (3) WebXR input validation and logging (L10 mitigation: a logging framework; disclosed to Meta/WebXR/A-Frame). A 2025 follow-up by the same authors exists, content unread (L39, U47). | AUTHOR / INFER |
| What remains | Whether the **displayed** state, as opposed to the sent or rendered state, is observable outside the app. A compromised app's false approval (M23). Coordinated feedback forgery (M25; L24–L26 defenses exist). | INFER |
| Experiment feasibility | **Low on this host.** None of the six audited implementations is target-selection based; all stream poses or twists. A test would need a self-written stand-in (not a real-app result), a WebXR browser stack, or MoveIt Pro (closed). | environment gap |
| Equipment | a target-selection XR app (real), a renderer we can instrument, possibly a headset | blocker |
| Expected information | High novelty potential, but the first run would be a stand-in or literature-only exercise | INFER |

## Comparison with M39 (detail in C01)

| Criterion | M39 (stop → hold → re-arm → re-reference) | M12 (stamp meaning) | M22 (scene → target) |
|---|---|---|---|
| A real XR→ROS path exists here | **yes** (F3 UR5e path; Gazebo consumer) | yes (same path, modified-app arm) | **no** |
| Strongest baselines implementable | yes: controller hold; app re-anchor + fresh press (app copy); epoch/cause re-arm | yes: sample-time stamping + age check | partially (stand-in) |
| A known confound to remove | yes: the singularity masking (U46). It is fixable by pose qualification. | minor | n/a |
| Open question that the matrix needs answered | Is the *combined* contract met by per-app fixes, and at what integration cost? Is ROS-side re-basing enough without app changes? | Does sample-time stamping close M12/M2 for an honest app, and what remains (inferred poses, buttons)? | Is the displayed state observable; does version checking suffice? |
| Can a common-structure claim be tested | **yes**: a per-app fix vs a ROS-side transition component, same evidence | weakly (the fix is per-app by nature) | not yet |
| Expected value of the first run | **removes the masked physical outcome of F3/P1 and tests the only plausible system benefit in this axis** | confirms a known fix plus a residual | blocked |

**Recommendation.** First experiment = **a scoped M39 pilot on the real UR5e path** (draft:
`../reports/R01_FIRST_EXPERIMENT_DRAFT_PROTOCOL.md`). M12 is the second candidate and can share
the same stack. M22 is recorded as BLOCKED_ENV until a target-selection XR→ROS app or an
instrumentable renderer is available.
