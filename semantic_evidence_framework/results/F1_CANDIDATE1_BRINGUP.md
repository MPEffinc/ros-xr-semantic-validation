# F1 candidate 1 bring-up — OpenVR UR5e app on xrizer on Monado main (2026-10-02): BLOCKED_ENV

Feasibility smoke runs; not measured trials. Raw data: `results/raw/F1/smoke_01`, `smoke_02` (ignored).

## Built (unmodified upstream, pinned)

| Component | Pin | Image | Build time |
|---|---|---|---|
| Monado main, with `libmonado` and the service | `045931d12f1c` (2026-09-30) | `f1-monado-main:045931d` (`docker/Dockerfile.monado`) | about 2 min |
| xrizer | `0989a7fac2d1` | `f1-xrizer:0989a7f` (`docker/Dockerfile.xrizer`) | about 2.5 min |
| pyopenvr | `openvr==2.12.1401` (PyPI) | same | — |

The app is `quest_teleop.py` @ 170dad5, unmodified; it uses the P1 workspace build.

## What happened

1. **libmonado query kills the runtime.** In smoke_01, calling `mnd_root_get_client_session_running_state` for a
   client that has no session (the collector itself) terminated `monado-service`. The client logged
   `ipc_receive: wrong size '0', expected '12'`, and every other client lost its connection.
   Reproduced in isolation. The collector no longer makes this call; it uses only
   `mnd_root_get_client_state` flags.
   - This is an availability property of the evidence path. A local IPC client can crash the
     runtime, so a compromised local app could do the same.
   - An upstream report was not searched.
2. **xrizer cannot create its Vulkan device in the container.**
   - With lavapipe (Mesa 25 llvmpipe, the only Vulkan driver available in the container), xrizer
     panics: `Could not create temporary vulkan device: ERROR_EXTENSION_NOT_PRESENT`
     (`src/graphics_backends/vulkan.rs` ≈L570–581).
   - xrizer enables every extension returned by `xrGetVulkanDeviceExtensionsKHR` (L549–556).
     Monado includes its *optional* `VK_KHR_external_semaphore_fd` / `VK_KHR_external_fence_fd`
     (`oxr_vulkan.c` L159–162 @ 045931d). lavapipe lacks both, so the combination fails although
     Monado itself treats them as optional.
   - The host NVIDIA GTX 1050 Ti (driver 580.173.02) cannot be used in the container: there is no
     nvidia-container-runtime. Bind-mounting the driver's user-space libraries and device nodes loads
     the ICD, but `vk_icdGetInstanceProcAddr` returns no `vkCreateInstance`. The cause was not found
     within the budget. The host `vulkaninfo` works.
3. Not reached: the session state of a Background OpenVR app on xrizer (the FOCUSED risk in
   `APP_COMPATIBILITY.md`), grip visibility, and command output (0 commands recorded).

## Verdict (stop rule applied, nothing modified)

**Candidate 1 is BLOCKED_ENV on this host.** The blocker is the GPU/Vulkan environment, not the app.

Options that would unblock it were **not taken**, because each changes a deployment component or
the host:

- installing nvidia-container-toolkit (host change, needs approval);
- patching xrizer to request only the extensions the device supports (component modification);
- running the stack on the host with ROS installed natively.

This result does not show that candidate 1 is incompatible with Monado.
