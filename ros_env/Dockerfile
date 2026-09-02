FROM ros:humble-ros-base-jammy

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3-colcon-common-extensions \
        python3-numpy \
        python3-websocket \
        ros-humble-control-msgs \
        ros-humble-sros2 \
        ros-humble-demo-nodes-cpp \
        ros-humble-demo-nodes-py \
        ros-humble-geometry-msgs \
        ros-humble-rosidl-default-generators \
        ros-humble-rosbridge-suite \
        ros-humble-tf-transformations \
        ros-humble-tf2-ros \
        ros-humble-visualization-msgs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/ros2_ws

CMD ["bash"]
