# AgileX downstream boundary

`arm_ik_pose_node` is a source-visible native software decision boundary that emits `JointState`.
The original actual arm driver is a separately cloned `agx_arm_ctrl` dependency and is not
launched. A future safe dry run needs an isolated ROS environment, a documented no-op subscriber
after IK, and proof that no driver is started. Current consequence is `UNKNOWN`.
