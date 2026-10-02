"""Servo bring-up identical to the pinned ur5_servo.launch.py (servo_node part), except that
P1_SERVO_TIMEOUT (if set) overrides moveit_servo.incoming_command_timeout.  Used for every arm
so that only the parameter differs between B0 and D_TO."""
import os
import yaml
import launch
import launch_ros
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder("ur5_robot", package_name="ur5_moveit_config")
        .robot_description(file_path=os.path.join(
            get_package_share_directory("ur5_description"), "urdf", "ur5_robot.urdf.xacro"))
        .to_moveit_configs()
    )
    path = os.path.join(get_package_share_directory("ur5_moveit_config"), "config", "ur_servo.yaml")
    with open(path) as f:
        servo_params = yaml.safe_load(f)["moveit_servo"]
    if os.environ.get("P1_SERVO_TIMEOUT"):
        servo_params["incoming_command_timeout"] = float(os.environ["P1_SERVO_TIMEOUT"])
    servo_node = launch_ros.actions.Node(
        package="moveit_servo", executable="servo_node", name="servo_node", namespace="/",
        parameters=[moveit_config.robot_description, moveit_config.robot_description_semantic,
                    moveit_config.robot_description_kinematics, moveit_config.joint_limits,
                    {"moveit_servo": servo_params}, {"use_sim_time": True}],
        output="screen")
    return launch.LaunchDescription([servo_node])
