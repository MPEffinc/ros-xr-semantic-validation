import rclpy
from rclpy.node import Node
import openvr
from geometry_msgs.msg import PoseStamped
from scipy.spatial.transform import Rotation as R
import sys

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
        
        self.timer = self.create_timer(0.02, self.timer_callback) # 50Hz

    def timer_callback(self):
        poses_type = openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount
        poses = poses_type()
        self.vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseRawAndUncalibrated, 0, poses)
        
        for i in range(openvr.k_unMaxTrackedDeviceCount):
            if self.vr.getTrackedDeviceClass(i) == openvr.TrackedDeviceClass_Controller:
                role = self.vr.getControllerRoleForTrackedDeviceIndex(i)
                
                if role == openvr.TrackedControllerRole_RightHand and poses[i].bPoseIsValid:
                    
                    # 1. Grip Button Check
                    result, state = self.vr.getControllerState(i)
                    is_gripping = bool(state.ulButtonPressed & (1 << openvr.k_EButton_Grip))

                    if not is_gripping:
                        if not self.first_packet:
                            self.get_logger().info("Teleop Disengaged.")
                        self.first_packet = True 
                        return

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
                    # Moves relative to a 40cm forward / 30cm up starting point
                    msg.pose.position.x = ((raw_x - self.offset_x) * self.scaling) + 0.4
                    msg.pose.position.y = ((raw_y - self.offset_y) * self.scaling)
                    msg.pose.position.z = ((raw_z - self.offset_z) * self.scaling) + 0.3

                    # ROTATION LOGIC (The Fix)
                    # Hand Relative Change = Initial_Hand_Inv * Current_Hand
                    hand_relative_rotation = self.offset_rot_inv * current_rot
                    
                    # Target = Robot_Home * Hand_Relative_Change
                    final_rot = self.robot_home_rot * hand_relative_rotation
                    quat = final_rot.as_quat()

                    msg.pose.orientation.x = quat[0]
                    msg.pose.orientation.y = quat[1]
                    msg.pose.orientation.z = quat[2]
                    msg.pose.orientation.w = quat[3]

                    self.publisher_.publish(msg)

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
