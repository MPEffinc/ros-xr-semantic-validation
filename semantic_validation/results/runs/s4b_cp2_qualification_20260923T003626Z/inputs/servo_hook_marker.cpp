// Qualification-only probe: exported Servo callback interposition feasibility.
// It changes no ROS message or control decision and always calls the original.
// This marker does not yet establish a source-ID join or consumer qualification.
#include <dlfcn.h>
#include <fcntl.h>
#include <time.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>

using Callback = void (*)(void*, const void*);

static void log_and_forward(const char* symbol, const char* stage,
                            void* self, const void* message_ref) {
  timespec ts{};
  clock_gettime(CLOCK_MONOTONIC, &ts);
  const char* path = getenv("XR_SERVO_HOOK_LOG");
  if (path) {
    int fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0666);
    if (fd >= 0) {
      char line[256];
      const int count = snprintf(line, sizeof(line),
          "{\"stage\":\"%s\",\"monotonic_ns\":%lld,\"message_ref\":\"%p\"}\n",
          stage, static_cast<long long>(ts.tv_sec) * 1000000000LL + ts.tv_nsec,
          message_ref);
      if (count > 0 && count < static_cast<int>(sizeof(line))) write(fd, line, count);
      close(fd);
    }
  }
  auto original = reinterpret_cast<Callback>(dlsym(RTLD_NEXT, symbol));
  if (!original) _exit(127);  // Never silently replace the original callback.
  original(self, message_ref);
}

extern "C" void hook_humble_twist(void*, const void*)
    __asm__("_ZN12moveit_servo10ServoCalcs14twistStampedCBERKSt10shared_ptrIKN13geometry_msgs3msg13TwistStamped_ISaIvEEEE");
extern "C" void hook_humble_twist(void* self, const void* message_ref) {
  log_and_forward("_ZN12moveit_servo10ServoCalcs14twistStampedCBERKSt10shared_ptrIKN13geometry_msgs3msg13TwistStamped_ISaIvEEEE",
                  "humble_twist_callback", self, message_ref);
}

extern "C" void hook_jazzy_pose(void*, const void*)
    __asm__("_ZN12moveit_servo9ServoNode12poseCallbackERKSt10shared_ptrIKN13geometry_msgs3msg12PoseStamped_ISaIvEEEE");
extern "C" void hook_jazzy_pose(void* self, const void* message_ref) {
  log_and_forward("_ZN12moveit_servo9ServoNode12poseCallbackERKSt10shared_ptrIKN13geometry_msgs3msg12PoseStamped_ISaIvEEEE",
                  "jazzy_pose_callback", self, message_ref);
}
