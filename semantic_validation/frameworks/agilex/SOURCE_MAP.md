# AgileX source map and limitation

| Chain stage | Pinned source | Observed boundary |
| --- | --- | --- |
| Native XR semantic/source decision | bundled `teleop-debug.apk` | `SOURCE_PATH_UNCONFIRMED`: source is not included. |
| Device bridge | `oculus_reader.py:47-52,140-200` | ADB launches package `com.rail.oculus.teleop`, parses tagged logcat into left/right 4×4 matrices plus buttons; no tracking validity, source time, sequence or session field is carried. |
| ROS pose | `pub_pose.py:114-132` | non-null left/right matrices are coordinate-converted, host-stamped, and published as `PoseStamped`/TF. |
| Control gate | `pub_delta_pose.py:176-227` | A/B buttons set a host-side teleop flag; delta pose is host-stamped and published. |
| IK handoff | `arm_ik_pose_node.py:325-360` | `/delta_pose` is solved by Pinocchio and published as `pin_joint_status` `JointState`; physical `agx_arm_ctrl` is external. |

The public host path is mapped, but the raw XR semantic source/first native gate is not. This
prevents inclusion under the V2 semantic-audit criterion.
