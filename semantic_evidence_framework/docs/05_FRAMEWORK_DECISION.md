# 05 — Framework expansion decision (brief §8), 2026-10-01

**Decision: do not build a general framework yet.** The next step is limited to an **independent
evidence-path feasibility study** (P2, Monado). It is a precondition for any framework claim.

## Evidence for each §8 condition

| Condition | Status | Evidence |
|---|---|---|
| 1. The same evidence/transition/enforcement requirement recurs across structurally different implementations | **Met at source level.** R1–R5 (tracked, activity/cause, recenter epoch, device identity, sample time) are lost in all 6 audited implementations, across 5 transport formats. | `04_RETROFIT_SITES.md`; audits A1–A6; R0 (real-device data for R2 and R4) |
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

**Kill criteria:**

- The runtime cannot expose the facts headless or independently.
- The linkage requires per-app edits equal to direct delivery.

## Kept as matrix results (solved cases)

| Case | Solution |
|---|---|
| M1 / M2 | transport + check (S5) |
| M3 | controller-level hold (P1b) |
| M4 | cause-aware re-arm *given* activity evidence (P1) |
| M6 | epoch gate or app retrofit *given* an epoch (P1) |
| M7 | stamped tf lookup |
| M8 | per-publish allocation (R0, code) |
| M11 | QoS/permission/timeout |
| M15 | standard authentication |
