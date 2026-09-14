FROM ros:jazzy-ros-base

# Simulation-only downstream environment for the pinned OpenVR UR5e target.
# Contains NO ur_robot_driver and NO hardware interface package: the pinned
# repository has no physical-driver path (verified: zero matches for
# robot_ip / ur_robot_driver / any IP literal), and none is added here.
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3-scipy \
      python3-colcon-common-extensions \
      ros-jazzy-xacro \
      ros-jazzy-moveit \
      ros-jazzy-moveit-servo \
      ros-jazzy-ros-gz-sim \
      ros-jazzy-ros-gz-bridge \
      ros-jazzy-gz-ros2-control \
      ros-jazzy-ros2-control \
      ros-jazzy-ros2-controllers \
      ros-jazzy-controller-manager \
      ros-jazzy-joint-state-broadcaster \
      ros-jazzy-joint-trajectory-controller \
      ros-jazzy-robot-state-publisher \
      ros-jazzy-rclcpp-components \
      xvfb \
 && rm -rf /var/lib/apt/lists/*
