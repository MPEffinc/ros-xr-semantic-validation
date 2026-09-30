# COPY of openvr_ur5e_jazzy@170dad5 src/ur5_moveit_config/launch/ur5_servo.launch.py (original untouched).
# Change: servo_node only (robot_state_publisher container already runs from the first launch), and
# moveit_servo parameters overridden from env N1_SERVO_OVERRIDES (JSON), e.g. {"use_smoothing": true}.
import os
import yaml
import launch
import launch_ros
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder
from launch.actions import TimerAction


def generate_launch_description():

    moveit_config = (
        MoveItConfigsBuilder("ur5_robot", package_name="ur5_moveit_config")
        .robot_description(
            file_path=os.path.join(
                get_package_share_directory("ur5_description"),
                "urdf",
                "ur5_robot.urdf.xacro",
            )
        )
        .to_moveit_configs()
    )

    servo_yaml_path = os.path.join(
        get_package_share_directory("ur5_moveit_config"),
        "config",
        "ur_servo.yaml",
    )

    with open(servo_yaml_path, "r") as f:
        servo_params = yaml.safe_load(f)
    import json as _json
    servo_params["moveit_servo"].update(_json.loads(os.environ.get("N1_SERVO_OVERRIDES", "{}")))

    servo_node = launch_ros.actions.Node(
        package="moveit_servo",
        executable="servo_node",
        name="servo_node",
        namespace="/",
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
            {"moveit_servo": servo_params["moveit_servo"]},  # ✅ correct nesting
            {"use_sim_time": True},
        ],
        output="screen",
    )

    container = launch_ros.actions.ComposableNodeContainer(
        name="ur_servo_container",
        namespace="/",
        package="rclcpp_components",
        executable="component_container_mt",
        composable_node_descriptions=[
            launch_ros.descriptions.ComposableNode(
                package="robot_state_publisher",
                plugin="robot_state_publisher::RobotStatePublisher",
                name="robot_state_publisher",
                parameters=[
                    {
                        "robot_description": moveit_config.robot_description[
                            "robot_description"
                        ]
                    },
                    {"use_sim_time": True},
                ],
            ),
        ],
        output="screen",
    )

    delayed_servo = TimerAction(period=5.0, actions=[servo_node])

    return launch.LaunchDescription([servo_node])
