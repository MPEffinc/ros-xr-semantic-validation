// External, non-defensive MoveIt Servo callback observer. It forwards each
// callback unchanged to the installed library and logs only after return.
// Source IDs are NOT inserted into the ROS message; joins must prove unique
// full message fields + original header stamp from the publisher trace.
#include <dlfcn.h>
#include <fcntl.h>
#include <time.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <geometry_msgs/msg/twist_stamped.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>

static long long monotonic_ns() {
  timespec ts{};
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return static_cast<long long>(ts.tv_sec) * 1000000000LL + ts.tv_nsec;
}

static void append_line(const char* line, int count) {
  const char* path = getenv("XR_SERVO_HOOK_LOG");
  if (!path || count <= 0) return;
  int fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0666);
  if (fd >= 0) {
    const auto written = write(fd, line, static_cast<size_t>(count));
    (void)written;
    close(fd);
  }
}

using Twist = geometry_msgs::msg::TwistStamped;
using Pose = geometry_msgs::msg::PoseStamped;
using TwistFn = void (*)(void*, const std::shared_ptr<const Twist>&);
using PoseFn = void (*)(void*, const std::shared_ptr<const Pose>&);

extern "C" void hook_humble_twist(void*, const std::shared_ptr<const Twist>&)
    __asm__("_ZN12moveit_servo10ServoCalcs14twistStampedCBERKSt10shared_ptrIKN13geometry_msgs3msg13TwistStamped_ISaIvEEEE");
extern "C" void hook_humble_twist(void* self, const std::shared_ptr<const Twist>& msg) {
  static auto original = reinterpret_cast<TwistFn>(dlsym(RTLD_NEXT,
      "_ZN12moveit_servo10ServoCalcs14twistStampedCBERKSt10shared_ptrIKN13geometry_msgs3msg13TwistStamped_ISaIvEEEE"));
  if (!original) _exit(127);
  const long long entry = monotonic_ns();
  original(self, msg);
  const long long returned = monotonic_ns();
  if (!msg) return;
  const auto& h = msg->header;
  const auto& t = msg->twist;
  char line[768];
  int count = snprintf(line, sizeof(line),
      "{\"stage\":\"humble_twist_callback_returned\",\"entry_ns\":%lld,\"returned_ns\":%lld,"
      "\"stamp_sec\":%d,\"stamp_nanosec\":%u,\"frame_id\":\"%s\","
      "\"linear\":[%.17g,%.17g,%.17g],\"angular\":[%.17g,%.17g,%.17g]}\n",
      entry, returned, h.stamp.sec, h.stamp.nanosec, h.frame_id.c_str(),
      t.linear.x, t.linear.y, t.linear.z, t.angular.x, t.angular.y, t.angular.z);
  if (count > 0 && count < static_cast<int>(sizeof(line))) append_line(line, count);
}

extern "C" void hook_jazzy_pose(void*, const std::shared_ptr<const Pose>&)
    __asm__("_ZN12moveit_servo9ServoNode12poseCallbackERKSt10shared_ptrIKN13geometry_msgs3msg12PoseStamped_ISaIvEEEE");
extern "C" void hook_jazzy_pose(void* self, const std::shared_ptr<const Pose>& msg) {
  static auto original = reinterpret_cast<PoseFn>(dlsym(RTLD_NEXT,
      "_ZN12moveit_servo9ServoNode12poseCallbackERKSt10shared_ptrIKN13geometry_msgs3msg12PoseStamped_ISaIvEEEE"));
  if (!original) _exit(127);
  const long long entry = monotonic_ns();
  original(self, msg);
  const long long returned = monotonic_ns();
  if (!msg) return;
  const auto& h = msg->header;
  const auto& p = msg->pose;
  char line[768];
  int count = snprintf(line, sizeof(line),
      "{\"stage\":\"jazzy_pose_callback_returned\",\"entry_ns\":%lld,\"returned_ns\":%lld,"
      "\"stamp_sec\":%d,\"stamp_nanosec\":%u,\"frame_id\":\"%s\","
      "\"position\":[%.17g,%.17g,%.17g],\"orientation\":[%.17g,%.17g,%.17g,%.17g]}\n",
      entry, returned, h.stamp.sec, h.stamp.nanosec, h.frame_id.c_str(),
      p.position.x, p.position.y, p.position.z,
      p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w);
  if (count > 0 && count < static_cast<int>(sizeof(line))) append_line(line, count);
}
