# 02 — Requirements and threat model (initial; revised as audits land)

## 1. What is protected

The protected task condition is that **a robot motion command is executed only while the evidence that
made it applicable still holds**, and that a motion command does not resume under evidence from a
different interval. "Evidence" is defined in `01_BACKGROUND.md`.

The robot task policy must be declared separately from XR runtime rules. For example, OpenXR
deactivating an action is **not** by itself a policy to cancel every robot task. Each experiment
declares the following:

| Policy element | Must be declared per experiment |
|---|---|
| Manipulation permission | which evidence must hold for a motion command to be admitted (e.g., deadman/clutch active, pose tracked, session focused) |
| Interruption | what happens to *in-flight* commands and *already-executing* goals when evidence lapses (filter only / zero-velocity stop / cancel goal / hold position) |
| Resume | what fresh evidence is needed to resume (rising edge, dwell, re-anchor to the current EE pose) |
| Allowed normal transitions | which state changes are legitimate and must not be blocked (recentering by the user, profile change, controller hand-off) |

Distinguish three outcomes. *Message filtered* means no further command is published. *Executing goal
stopped* means a Servo or trajectory goal is cancelled or zeroed. *Physically stopped* means the
joint velocity has dropped to about 0. These must never be conflated.

## 2. Events that must not be merged

Each of the following is a separate event with a separate cause, injection point and oracle:

| Event | Origin | Legitimate? |
|---|---|---|
| E-ORIGIN: runtime reference-space change (OpenXR `XrEventDataReferenceSpaceChangePending`, user recenter) | XR runtime / user | yes, normal |
| E-CALIB: application calibration or anchor update (app re-captures an offset or a world anchor) | XR app | yes, normal |
| E-DRIFT: natural tracking drift or relocalization | tracking system | yes, but degrades accuracy |
| E-TF-FORGE: an attacker publishes a forged `/tf` or a calibration message | attacker on the ROS graph | no |
| E-DEACT: action set deactivated / session loses focus (`isActive=false`) | XR runtime | yes, normal |
| E-TRACK: pose not tracked (`*_TRACKED_BIT` cleared, `bPoseIsValid=false`) | tracking system | yes, normal |
| E-DISC: transport disconnect / reconnect | network / app | yes, normal |

## 3. Threat / fault model

| Actor | Capability | In scope? |
|---|---|---|
| F0 benign faults | the transitions above occurring at arbitrary times relative to command generation and consumption | **primary scope** (safety/consistency) |
| A1 network peer on an unauthenticated bridge (rosbridge, TCP endpoint, UDP) | inject or replay XR messages | in scope only as *already-known class*. Unauthenticated bridges are a documented, acknowledged gap with a standard remedy (TLS/SROS2/auth). It is **not** a research gap. |
| A2 ROS-graph participant | publish `/tf`, calibration and command topics | in scope for E-TF-FORGE; the standard remedy is SROS2 access control on those topics |
| A3 compromised XR app | arbitrary self-reported fields | **out of scope for any claim** unless an evidence path exists that the app cannot modify (runtime- or OS-level). Signing self-reported fields does not defend against A3. |

**Trust boundaries** are recorded per implementation in `../audit/`. A defense counts only for the
boundary at which it sits. For example, a source-side gate does not cover delay introduced after its
decision (S5, PLACEMENT class).

**SROS2 note.** SROS2 does not judge tracking validity. That is outside its protection goal, not a
gap.

## 4. Evidence labels

| Label | Meaning |
|---|---|
| `AUTHOR_CLAIM` | stated in a README, paper or comment, not checked in code |
| `SOURCE_CONFIRMED` | read in code at a pinned commit (file, function, lines) |
| `HYPOTHESIS` | proposed, not yet tested |
| `EXPERIMENT_CONFIRMED` | observed in a run in this study (raw data hashed in `../results/`) |
| `NOT_VERIFIED` | not checked, or impossible to check here; **never evidence of a gap** |
| `PRIOR_INTERNAL` | result of an earlier internal study; background only |

A `?` in any matrix means NOT_VERIFIED.

## 5. Scope statements

- The OpenXR items selected for the taxonomy are those that bear on applicability evidence:
  - action state;
  - session state;
  - space-location flags;
  - reference-space change;
  - interaction-profile change;
  - time.

  Covering these items is **not** a claim that the specification is complete. Nor is it a claim that
  app-, vendor- or physical-environment behaviour is complete.
- Synthetic inputs test ROS-side consumption only. They do not reproduce a real runtime or headset
  transition.
