FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3-scipy python3-colcon-common-extensions \
 && rm -rf /var/lib/apt/lists/*
