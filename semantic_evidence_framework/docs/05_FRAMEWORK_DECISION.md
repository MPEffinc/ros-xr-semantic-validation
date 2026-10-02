# 05 — Framework expansion decision (brief §8), 2026-10-01

**Decision: do not build a general framework yet.** (Scope of "solved": `06_CLAIM_SCOPE_CORRECTION.md`.) The next step is limited to an **independent
evidence-path feasibility study** (P2, Monado). It is a precondition for any framework claim.

## Evidence for each §8 condition

| Condition | Status | Evidence |
|---|---|---|
| 1. The same evidence/transition/enforcement requirement recurs across structurally different implementations | **Met for the ROS-facing interface.** R1–R5 (tracked, activity/cause, recenter epoch, device identity, sample time) are absent from the wire/consumer in all 6 audited implementations, across 5 transport formats. API provision is known for 4/6; app reading is confirmed only in a few cases (`06`). | `04_RETROFIT_SITES.md`; audits A1–A6; R0 (real-device data for R2 and R4) |
| 2. Manual retrofits need implementation-specific, repeated edits | **Met at source level.** Each fix lands at a different site: ALVR client, Unity script, browser JS, UDP bridge, ROS node. 2 of 6 frontends are closed binaries. OpenVR legacy has no slot for R2/R3. The app-side recenter fix (EPOCH_A, 15 lines) needs app-specific offset semantics. | `04`; P1 §3 |
| 3. A common model gives the same guarantee with fewer edits, lower latency or fewer false blocks | **Not shown.** | see below |

### What P1/P1b do and do not support for condition 3

**Supported.** Once the evidence is delivered, *generic* consumer-side rules suffice:

- cause-aware re-arm (REARM_C) passes both the residual-permission case and the false-block control;
- an epoch gate stops recenter jumps without app knowledge;
- a controller-level hold stops release motion.

These are conventional mechanisms: S5 re-arm, epochs as sequencers, JTC hold. *Their* novelty is
**not** claimed.

**Not supported.**

- That a *common model* reduces edits. The edits that remain are almost all **evidence delivery** at
  the source. A ROS-side framework cannot remove them.
- That it would be better than S5's I_FULL envelope + gate. S5 already showed that pattern
  (PRIOR_INTERNAL). FlowTags is prior art for tagging causal context.
- Latency or false-block advantages over per-implementation fixes. They were not measured, and with
  equal evidence they are not expected to differ.

## What would change the decision

A framework contribution becomes plausible only if the evidence can be obtained **without modifying
each app**, through a path the app cannot rewrite:

- **Runtime-side collector** (out of process, e.g. inside the Monado service or the SteamVR driver
  layer). It is independent of a compromised app. It covers runtime-owned facts: activity/focus,
  tracked flags, reference-space change with `changeTime`.
- **OpenXR API layer** (in process). It needs no app change, but it is **not** independent of a
  compromised app (A3), because it shares the address space.
- **Command ↔ sample linkage.** An independent collector still has to be joined to the app's commands.
  That requires the app to carry a sample id or `XrTime` (an app change), or a timing join with stated
  error. This is an open research question, not solved here.

**Go criteria for building the minimal framework**, as specified in the brief:

1. A runtime-side or layer collector reports R2/R3 for **at least two unmodified apps**.
2. A ROS consumer enforces with it, with an error at or below a stated level.
3. It achieves the P1 REARM_C / EPOCH_G guarantees **with fewer per-implementation edits** than
   delivering the fields app by app.

**Kill criteria** (revised 2026-10-02):

- A single environment failure, such as one headless Monado build, does **not** kill the path.
  The path is killed only if the evidence cannot be collected independently in any feasible runtime
  configuration that the target apps actually run on.
- Collecting state alone is not success: it must be linked to commands at a stated guarantee level.
- The linkage requires per-app edits equal to direct delivery.

## Kept as matrix results

| Case | Solution | Executed? |
|---|---|---|
| M1 | transport + check | PRIOR_INTERNAL (S5) |
| M2 (frozen stream) | transport of activity + check | **not executed** |
| M3 | controller-level hold | P1b |
| M4 | cause-aware re-arm *given* activity evidence | P1 (command level) |
| M6 | epoch gate or app retrofit *given* an epoch | P1 |
| M7 | stamped tf lookup | not executed |
| M8 | per-publish allocation | not executed (R0 shows the defect; the fix is untested) |
| M11 | QoS/permission/timeout | not executed |
| M15 | standard authentication | not executed |

## Update 2026-10-02 — limited feasibility study F1 (independent evidence path)

Sources: `results/P2_CAUSE_ANALYSIS.md`, `experiments/F1_independent_evidence/APP_COMPATIBILITY.md`,
`results/F1_CANDIDATE1_BRINGUP.md`, `results/F1_CANDIDATE2_ISAACTELEOP.md`,
`results/F1_LINKAGE_RESULTS.md`.

| Revised criterion (brief step 8) | Finding |
|---|---|
| A headless failure alone does not kill the path | Correct. The 2023 Monado build was the cause. The current build works headless. |
| State collection alone is not success | **State-level command linkage was achieved, with a stand-in app.** C_INTERVAL: 0 dangerous passes and 0 false blocks outside an evidence outage, across late, reordered, replayed, cross-client and delayed-evidence cases. Sample-level provenance was **not** achieved. |
| Per-app changes compared with direct delivery | 0 app-side sites (independent path) vs. one read + publisher/message change per app (direct). For an honest app the guarantee is identical, because D_STREAM matches it. |
| Stronger trust boundary? | **No, in this pilot.** libmonado control calls are unauthenticated on the app's own IPC socket, and client identity is self-reported. |
| Real apps | **0 of 2 candidates functional on this host.** The OpenVR UR5e app needs an xrizer that drives frames for Background apps. IsaacTeleop needs NVIDIA NVX1 extensions. The other 5 audited frontends are not Linux/Monado apps. |

**Decision: expansion stays on hold** (`보류`). It is *not* killed: the mechanism works and its one
clear advantage (no app-side edits) was measured. But the brief's condition, "fewer per-app changes
for apps that actually need the guarantee", cannot be shown while no real app runs on a runtime that
exposes this evidence.

**What would justify building the minimal system** (in priority order):

1. **A real XR→ROS app running functionally on Monado**, ideally an ordinary immersive OpenXR app
   with a frame loop, or the OpenVR UR5e app on an xrizer with a frame pump (a component change,
   reported separately). Then repeat F1 with no app change.
2. **Focus/tracking evidence for non-headless clients**: service flags for a compositor-backed
   client, which needs a working GPU path in the container or on the host.
3. **For any S2 claim:** authenticated control calls, or socket separation in the runtime. That
   means modifying the runtime, with results kept separate from the unmodified build.

No new checking algorithm is needed. The candidate contribution would be the *runtime-sourced
evidence path with lifetime-interval enforcement at the consumer* and its measured zero-app-change
property. That is a system contribution, provided the conditions above are met.
