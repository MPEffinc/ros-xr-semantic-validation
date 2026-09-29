# FRAMEWORK: Nakama VR_Teleop_Interface

## Identity

- Repository: `https://github.com/nakama-lab/VR_Teleop_Interface.git`
- Revision: `aebf6394a16d9ee9b95aaa209c59f9788cb038bb` (2025-04-30, "Update README.md"), worktree clean
- Local checkout: `semantic_validation/targets/nakama_vr_teleop`
- Clone state: **shallow, single commit, single branch `main`**

## Critical identity finding — the code is not in this repository

The audit brief assumed Unity and ROS/Franka code lived on other **branches of this repository**.
That is **not what the source shows**:

- `git branch -a` lists only `main` and its remote-tracking ref. `.git/config` fetch refspec is
  `+refs/heads/main:refs/remotes/origin/main`. No other branch exists locally or on this origin, so
  `git ls-tree` against any other branch name fails with `fatal: Not a valid object name`.
- `README.md:81-83,90-92` states the code branches (`aorus_zed`, `unity_vr`, `cubi`) live in a
  **different account's fork**: `JuanR5/VR_Teleop_Interface`.
- The entire working tree is: `LICENSE`, `README.md`, `.gitignore`, `.github/workflows/ci.yml`, and
  eight Markdown files under `docs/`. There is **no** `.cs`, `.py`, `.cpp`, `package.xml`,
  `CMakeLists.txt`, launch file, or Unity project anywhere.
- `.github/workflows/ci.yml:17-21` checks this repository out into `src/franka_ros2` inside a
  `franka_ros2:humble` image — a vestigial template that cannot build anything present here.

Per `methodology/FRAMEWORK_SELECTION.md`, this candidate is therefore
**`SOURCE_PATH_UNCONFIRMED`** at the pinned identity. That is a source-availability outcome, not a
negative semantic finding about the project.

## Architecture (as documented, not as verified)

Every element below is a label in a README mermaid diagram, not auditable code:

```text
Quest 2 -> Unity ("Quest2ControllerInput.cs")  [named at README.md:35 only]
  -> Unity ROS TCP Connector                    [README.md:12,28,129]
  -> controller_movement [Twist], gripper_command [Float32MultiArray],
     zed2_unity images, rumble_output            [README.md:29-32]
  -> modify_pose.py, cartesian_impedance_controller.cpp, gripper_command.py
                                                 [named at README.md:96-99 only]
  -> Franka (franka_ros2, sp-sophia-labs fork)   [README.md:127-128]
```

## System Relevance

- Classification: **`CANDIDATE_IDENTITY_UNCONFIRMED`** at this revision. If the `JuanR5` fork is
  resolved and pinned, the documented design would plausibly be `HIGH_XR_ROS_CONTROL`.

## Semantic Observability

All axes: **NOT AUDITABLE AT THIS IDENTITY.** Repo-wide grep for every tracking-validity token
returns zero hits because there is no code to grep. Sequence diagrams in
`docs/SequenceDiagrams/CommandPub.md:16` ("Validate command") and
`docs/SequenceDiagrams/RobotControl.md:23-35` ("Out of Range", "Mechanical Failure") describe
intent, not implementation, and must not be cited as evidence of a gate.

## Control Depth

- Last auditable boundary: the README text itself. Nothing executable exists.
- Physical driver dependency: a real Franka would be required for the documented design; none of it
  is present here, so there is nothing in this checkout that could contact hardware.

## Testbed Adaptation

Not applicable at this identity — nothing to build, launch, or stub.

## Quest-less Potential

None at this identity.

## Future Quest Test

Not schedulable until the source identity is resolved.

## Research Value

- Current value: **methodological**. It is a concrete example of why the selection policy requires
  a verified source chain before a candidate is counted: a plausible-looking, institutionally
  affiliated "Quest → ROS 2 → Franka Cartesian impedance" project contributes **zero** auditable
  semantics at its canonical repository.
- It also warns against inflating population counts from README architecture diagrams.

## Weaknesses

- No source at the pinned identity.
- The real code is in a third-party fork whose canonical status, license, and revision are
  unverified. Resolving it would require confirming that `JuanR5/VR_Teleop_Interface` is the
  intended artefact rather than a personal working copy.

## Final Role

- **`EXCLUDED`** from the principal, positive-control, and auxiliary populations at revision
  `aebf639`.
- Retained in the ledger as a **screened candidate** with an explicit
  `SOURCE_PATH_UNCONFIRMED` disposition.

## Priority

**DROP** at this identity. Re-open only if `JuanR5/VR_Teleop_Interface` is verified as the
canonical source and can be pinned; the documented Franka Cartesian-impedance consumer would then
make it a genuinely interesting `NATIVE_CONSUMER` candidate.
