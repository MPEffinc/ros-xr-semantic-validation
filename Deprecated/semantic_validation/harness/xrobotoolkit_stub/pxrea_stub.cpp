/* INERT LOCAL SUBSTITUTE implementation for the proprietary PICO Robotics
 * Service SDK. See PXREARobotSDK.h. No network, no device, no robot.
 *
 * PXREAInit spawns one thread that reads newline-delimited synthetic
 * device-state JSON records from the file named by the environment variable
 * XRT_SYNTHETIC_JSON and delivers each one to the upstream callback exactly as
 * the real service would deliver a PXREADeviceStateJson event. When the file is
 * exhausted the thread exits. Nothing else is emulated.
 */
#include "PXREARobotSDK.h"

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <string>
#include <thread>

namespace {
std::thread g_thread;
std::atomic<bool> g_running{false};
}  // namespace

extern "C" void PXREAInit(void* reserved, PXREAClientCallback callback, int mask) {
  (void)reserved;
  (void)mask;
  const char* path = std::getenv("XRT_SYNTHETIC_JSON");
  if (path == nullptr || callback == nullptr) {
    return;
  }
  g_running = true;
  std::string file(path);
  g_thread = std::thread([callback, file]() {
    std::this_thread::sleep_for(std::chrono::milliseconds(1500));
    std::ifstream stream(file);
    std::string line;
    const char* device_id = "SYNTHETIC_LOCAL_STUB";
    while (g_running && std::getline(stream, line)) {
      if (line.empty()) {
        continue;
      }
      PXREADevStateJson state;
      state.deviceID = device_id;
      state.stateJson = line.c_str();
      callback(nullptr, PXREADeviceStateJson, 0, &state);
      std::this_thread::sleep_for(std::chrono::milliseconds(250));
    }
  });
}

extern "C" void PXREADeinit(void) {
  g_running = false;
  if (g_thread.joinable()) {
    g_thread.join();
  }
}
