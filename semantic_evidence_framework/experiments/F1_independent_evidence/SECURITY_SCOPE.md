# F1 security scope (fixed 2026-10-02, before the linkage experiment)

## Actors

| ID | Actor | Capabilities | In scope for which claim |
|---|---|---|---|
| S1 | **Honest app with mistakes** | It sends commands with correct stamps, but forwards no evidence, or stale evidence (as audits A1–A6 found), and may let middleware delay, reorder or replay commands | **All F1 claims** |
| S2 | **Compromised app with legitimate ROS send rights** | It publishes arbitrary commands with arbitrary stamps on its permitted topic, and opens any local IPC endpoint its user can open, including the Monado socket | **Only the specific claims marked S2 below.** Nothing is claimed against S2 merely because evidence is collected conveniently from an honest app. |
| — | Network attacker / other ROS participants | out of scope here: SROS2 / auth (matrix M15) | — |

## Trusted computing base assumed for the "independent" path

- `monado-service` (unmodified upstream main `045931d`) and the OS kernel.
- The runtime-side collector (`collector/mnd_collector.c`), which talks to the service through
  libmonado.
- The evidence channel from collector to gate: a FIFO, which in this pilot sits in the same
  container.
- The ROS gate at the consumer, and the consumer itself.
- Pilot limitation: all of these run in **one container under one uid**, so the OS does **not**
  enforce the separation between app and TCB here. A deployment would have to.

## Trust boundaries and bypass paths, with what F1 can and cannot claim

| Path | Bypass or forgery | Status in this pilot |
|---|---|---|
| Runtime state → collector | **libmonado control is unauthenticated.** The library that reads state also exposes setters (`mnd_root_set_client_focused`, `mnd_root_toggle_client_io_active`, `mnd_root_set_client_io_blocks`) over the **same** IPC socket that every OpenXR app must use. Any process that can run an OpenXR app can therefore change the runtime-reported state, including an app's own IO blocks. | Shown in the setup probe: `mnd_ctl` changed `sa_main`'s IO state from an ordinary process. **S2 can forge the source of truth.** Independence from a compromised app needs a runtime change (authorise control calls) or OS separation of the socket. Neither is done here. |
| Client identity | The client name and `pid` are **self-reported** (`ipc_client_connection.c` L333–340, "Extra info"). | Binding a ROS topic to a runtime client is by **deployment configuration**. S2 can register a decoy client name. |
| Command provenance | The ROS command's `header.stamp` (generation time) comes from the app | For S1 it is correct by assumption. For S2 the stamp can lie, so interval checks give **no** provenance guarantee against S2. |
| Gate → consumer | The gate must be the only path to the consumer (topic permissions) | Assumed, not enforced (no SROS2 in the pilot) |
| Collector availability | A local IPC client can crash `monado-service` with one libmonado query (`F1_CANDIDATE1_BRINGUP.md` §1) | Gates must fail closed on stale evidence. That gives safety under denial of service, not availability. |

## Claims allowed after F1, by actor

- **S1:** "Commands generated or arriving while the runtime reports the bound client's input inactive
  can be blocked *without app modification*." This rests on the runtime's state, not on app-reported
  fields. The measured error bounds are stated in the results.
- **S2:** at most "state-level blocking holds if the app cannot reach the runtime's control interface
  and cannot mint commands that appear to come from another bound client". In this pilot neither
  condition is enforced, so **no S2 defense is claimed**.
