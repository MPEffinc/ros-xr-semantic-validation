FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        jq \
        mosquitto \
        mosquitto-clients \
        netcat-openbsd \
        nlohmann-json3-dev \
        python3-colcon-common-extensions \
        python3-paho-mqtt \
        python3-pip \
        python3-rosdep \
        python3-venv \
        ros-jazzy-ament-cmake-gtest \
        ros-jazzy-ament-lint-auto \
        ros-jazzy-ament-lint-common \
        ros-jazzy-example-interfaces \
        ros-jazzy-nav2-bringup \
        ros-jazzy-nav2-loopback-sim \
        ros-jazzy-nav2-msgs \
        ros-jazzy-rclcpp-action \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/compas-venv \
    && /opt/compas-venv/bin/python -m pip install --no-cache-dir \
        "compas==2.15.0" \
        "compas_eve==2.1.1" \
        "compas_timber==0.7.0" \
        "pyrebase4==4.9.0" \
        "paho-mqtt==2.1.0"

ENV DEBIAN_FRONTEND=
WORKDIR /work
CMD ["bash"]
