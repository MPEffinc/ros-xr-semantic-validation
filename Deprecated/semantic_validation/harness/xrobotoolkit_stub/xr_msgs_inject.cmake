# Build-boundary substitution, injected via CMAKE_PROJECT_xr_msgs_INCLUDE.
# The upstream xr_msgs/CMakeLists.txt calls rosidl_generate_interfaces() but only
# does find_package(rosidl_generator_cpp), which on ROS 2 Jazzy does not define
# that macro. Rather than editing upstream source, the missing find_package is
# injected here by CMake's project-include hook.
find_package(rosidl_default_generators REQUIRED)
