"""M3_ordering: the M39 servo_launch.py with ONE optional change: if M3_REMAP=1, Servo's output topic
/ur5_arm_controller/joint_trajectory is remapped to /m3/servo_out (so that the multiplexer is the only writer to the
controller topic). Everything else identical (parameters, sim time)."""
import os, yaml, launch, launch_ros
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder
def generate_launch_description():
    moveit_config = (MoveItConfigsBuilder("ur5_robot", package_name="ur5_moveit_config")
                     .robot_description(file_path=os.path.join(get_package_share_directory("ur5_description"), "urdf", "ur5_robot.urdf.xacro"))
                     .to_moveit_configs())
    with open(os.path.join(get_package_share_directory("ur5_moveit_config"), "config", "ur_servo.yaml")) as f:
        servo_params = yaml.safe_load(f)["moveit_servo"]
    remaps = [("/ur5_arm_controller/joint_trajectory", "/m3/servo_out")] if os.environ.get("M3_REMAP") == "1" else []
    node = launch_ros.actions.Node(package="moveit_servo", executable="servo_node", name="servo_node", namespace="/",
        parameters=[moveit_config.robot_description, moveit_config.robot_description_semantic, moveit_config.robot_description_kinematics,
                    moveit_config.joint_limits, {"moveit_servo": servo_params}, {"use_sim_time": True}], remappings=remaps, output="screen")
    return launch.LaunchDescription([node])
