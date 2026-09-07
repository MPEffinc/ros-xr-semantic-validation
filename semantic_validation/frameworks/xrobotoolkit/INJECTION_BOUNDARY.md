# XRoboToolkit injection boundary

`/xr_pose` injection bypasses the proprietary PicoXR service and the ROS publisher's parsing/
status handling. It is `BOUNDARY_LIMITED_REPLAY`. No such replay was run because ARX `PosCmd`
is control-producing and no verified inert consumer/stub was available.
