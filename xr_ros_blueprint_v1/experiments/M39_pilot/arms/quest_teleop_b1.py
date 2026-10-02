import rclpy
from rclpy.node import Node
import openvr
from geometry_msgs.msg import PoseStamped
from scipy.spatial.transform import Rotation as R
import sys
# M39 B1 (strongest per-app fix): app copy of quest_teleop.py @170dad5. Every change is marked "B1:".
import os, time  # B1:
sys.path.insert(0, os.environ.get("M39_HARNESS", "/m39/harness"))  # B1: shared low-level core (counted separately)
from m39_transition import TransitionCore  # B1:
from m39_evidence import Evidence  # B1:

class QuestTeleop(Node):
    def __init__(self):
        super().__init__('quest_teleop_node')
        
        # Topic matches the 'pose_command_in_topic' in ur_servo.yaml
        self.publisher_ = self.create_publisher(PoseStamped, '/servo_node/pose_target_cmds', 10)
        
        # Initialize OpenVR
        try:
            self.vr = openvr.init(openvr.VRApplication_Background)
        except openvr.OpenVRError as e:
            self.get_logger().error(f"OpenVR Init Failed: {e}")
            sys.exit(1)

        # Calibration & Control State
        self.first_packet = True
        self.offset_x, self.offset_y, self.offset_z = 0.0, 0.0, 0.0
        self.offset_rot_inv = None
        
        # --- IMPROVED KINEMATICS SETTINGS ---
        self.scaling = 0.5  # Lowered to 0.5 for smoother, safer testing
        
        # Define a 'Neutral' orientation (Gripper pointing forward/down)
        # This prevents the IK solver from failing due to extreme wrist angles
        self.robot_home_rot = R.from_euler('xyz', [0, 1.57, 0]) 

        self.get_logger().info("Quest 3 MoveIt Servo Bridge: ONLINE.")
        self.get_logger().info("HOLD RIGHT GRIP: Robot follows hand.")
        self.get_logger().info("RELEASE GRIP: Robot stops; hand position resets.")
        
        # B1: (a) any interruption (pose invalid, runtime evidence not ok, grip release) disengages, stops publishing
        # B1:     and starts the ordered controller stop of the shared core;
        # B1: (b) re-engage needs a FRESH press: a grip=false reading taken while the pose is valid AND the runtime
        # B1:     evidence is ok, then grip=true. Readings while invalid/inactive are ignored (pre-flight probe: grip
        # B1:     reads false there and true again on reactivation without any release);
        # B1: (c) engage only once the hold is settled, re-anchored to the MEASURED EE (tf base_link->wrist_3_link)
        # B1:     instead of the constant (0.4, 0, 0.3) / robot_home_rot;
        # B1: (d) the first re-anchored target goes through the shared ordered resume (publish, then unpause).
        self.core = TransitionCore(self, os.environ["M39_ARM_LOG"])  # B1:
        self.ev = Evidence(os.environ["M39_EV_FIFO"])  # B1:
        self.engaged = False  # B1:
        self.need_release = True  # B1: a valid release must be seen before the first/next engage
        self.anchor_p, self.anchor_rot = None, None  # B1:
        self.last_why = None  # B1:
        self.prev_tick = 0.0  # B1:
        self.core.interrupt("startup")  # B1: start HELD so that the first engage uses the same ordered resume

        self.timer = self.create_timer(0.02, self.timer_callback) # 50Hz

    def b1_disengage(self, why):  # B1:
        if self.engaged:
            self.engaged = False
            self.core.interrupt(why)
        if why != "release":
            self.need_release = True
        if why != self.last_why:
            self.core.log("b1_" + why); self.last_why = why

    def timer_callback(self):
        poses_type = openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount
        poses = poses_type()
        self.vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseRawAndUncalibrated, 0, poses)
        ev_ok, ev_age, _, ev_flags, ev_bad = self.ev.state()  # B1:
        if ev_bad is not None and ev_bad > self.prev_tick:  # B1: latch a deactivation shorter than one app tick
            ev_ok = False
        self.prev_tick = time.time()  # B1:
        found = False  # B1:
        
        for i in range(openvr.k_unMaxTrackedDeviceCount):
            if self.vr.getTrackedDeviceClass(i) == openvr.TrackedDeviceClass_Controller:
                role = self.vr.getControllerRoleForTrackedDeviceIndex(i)
                
                if role == openvr.TrackedControllerRole_RightHand:  # B1: validity handled below instead of skipping
                    found = True  # B1:
                    if not poses[i].bPoseIsValid:  # B1:
                        self.b1_disengage("pose_invalid"); return  # B1:
                    if not ev_ok:  # B1:
                        self.b1_disengage("evidence_not_ok"); return  # B1:
                    
                    # 1. Grip Button Check
                    result, state = self.vr.getControllerState(i)
                    is_gripping = bool(state.ulButtonPressed & (1 << openvr.k_EButton_Grip))

                    if not is_gripping:
                        if not self.first_packet:
                            self.get_logger().info("Teleop Disengaged.")
                        self.first_packet = True 
                        self.b1_disengage("release")  # B1:
                        self.need_release = False  # B1: valid release observed
                        return

                    if not self.engaged:  # B1:
                        if self.need_release:  # B1: grip held through an interruption: no fresh press
                            if self.last_why != "await_fresh_press":
                                self.core.log("b1_await_fresh_press"); self.last_why = "await_fresh_press"
                            return
                        if not self.core.is_held():  # B1: wait for the settled hold before re-anchoring
                            return
                        ee = self.core.ee()  # B1:
                        if ee is None:  # B1:
                            return
                        self.anchor_p, self.anchor_rot = ee["p"], R.from_quat(ee["q"])  # B1:
                        self.first_packet = True  # B1: capture the hand offset now

                    # 2. Extract Data
                    matrix = poses[i].mDeviceToAbsoluteTracking
                    raw_x, raw_y, raw_z = float(matrix[0][3]), float(matrix[1][3]), float(matrix[2][3])
                    
                    current_rot_mtx = [
                        [matrix[0][0], matrix[0][1], matrix[0][2]],
                        [matrix[1][0], matrix[1][1], matrix[1][2]],
                        [matrix[2][0], matrix[2][1], matrix[2][2]]
                    ]
                    current_rot = R.from_matrix(current_rot_mtx)

                    # 3. Calibration on Grip
                    if self.first_packet:
                        self.offset_x, self.offset_y, self.offset_z = raw_x, raw_y, raw_z
                        self.offset_rot_inv = current_rot.inv()
                        self.first_packet = False
                        self.get_logger().info("Teleop Engaged: Relative tracking active.")

                    # 4. Construct Message
                    msg = PoseStamped()
                    msg.header.stamp = self.get_clock().now().to_msg()
                    msg.header.frame_id = "base_link" 

                    # POSITION LOGIC
                    # B1: relative to the measured EE at engage instead of the 40cm forward / 30cm up constant
                    msg.pose.position.x = ((raw_x - self.offset_x) * self.scaling) + self.anchor_p[0]  # B1:
                    msg.pose.position.y = ((raw_y - self.offset_y) * self.scaling) + self.anchor_p[1]  # B1:
                    msg.pose.position.z = ((raw_z - self.offset_z) * self.scaling) + self.anchor_p[2]  # B1:

                    # ROTATION LOGIC (The Fix)
                    # Hand Relative Change = Initial_Hand_Inv * Current_Hand
                    hand_relative_rotation = self.offset_rot_inv * current_rot
                    
                    # B1: Target = Measured_EE_at_engage * Hand_Relative_Change (was Robot_Home * ...)
                    final_rot = self.anchor_rot * hand_relative_rotation  # B1:
                    quat = final_rot.as_quat()

                    msg.pose.orientation.x = quat[0]
                    msg.pose.orientation.y = quat[1]
                    msg.pose.orientation.z = quat[2]
                    msg.pose.orientation.w = quat[3]

                    if not self.engaged:  # B1: first re-anchored target -> ordered resume
                        self.engaged = True; self.last_why = None
                        self.core.log("b1_engage", anchor_p=self.anchor_p, anchor_q=list(self.anchor_rot.as_quat()),
                                      ev_age=ev_age, ev_flags=ev_flags)
                        self.core.resume(msg, self.publisher_)
                        return
                    self.publisher_.publish(msg)
        if not found:  # B1: controller absent counts as pose invalid
            self.b1_disengage("pose_invalid")

def main(args=None):
    rclpy.init(args=args)
    node = QuestTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        openvr.shutdown()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
