/* INERT LOCAL SUBSTITUTE for the proprietary PICO Robotics Service SDK header.
 *
 * This file is NOT upstream. It exists solely so that the unmodified upstream
 * translation unit ros2/picoxr/src/publisher.cpp can be compiled and executed in
 * a robot-free, network-free container. It declares only the symbols that
 * publisher.cpp actually uses, inferred from that file's call sites.
 *
 * It contains no PICO code, performs no device discovery, opens no socket, and
 * cannot connect to any headset or robot. The accompanying implementation feeds
 * synthetic device-state JSON records from a local file.
 */
#ifndef PXREAROBOTSDK_STUB_H
#define PXREAROBOTSDK_STUB_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
  PXREAServerConnect = 0,
  PXREAServerDisconnect = 1,
  PXREADeviceFind = 2,
  PXREADeviceMissing = 3,
  PXREADeviceConnect = 4,
  PXREADeviceStateJson = 5,
  PXREADeviceCustomMessage = 6,
  PXREAFullMask = 0xFFFF
} PXREAClientCallbackType;

typedef struct {
  const char* deviceID;
  const char* stateJson;
} PXREADevStateJson;

typedef void (*PXREAClientCallback)(void* context, PXREAClientCallbackType type,
                                    int status, void* userData);

void PXREAInit(void* reserved, PXREAClientCallback callback, int mask);
void PXREADeinit(void);

#ifdef __cplusplus
}
#endif
#endif
