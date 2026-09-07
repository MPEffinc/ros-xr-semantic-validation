# LTS0429 downstream boundary

The rclcpp node can publish `headset`, `left_hand`, `right_hand` and `/tf`; a vendored MoveIt
Servo pose-tracking example is present but not connected/executed in this preparation. No
environment, mock driver, Pi integration, native consumer acceptance, actuator stub, or robot
was run. Future ROS receipt can establish only `ROS_PUBLISHED` or `PI_RECEIVED` unless the
original consumer is separately mapped and dry-run.
