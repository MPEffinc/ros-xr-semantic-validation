# R15 — M12 source stall: standard receive watchdog on the remote driver (protocol; frozen before formal runs, 2026-10-04)

## 1. Code path in the pinned Monado 045931d `remote` driver

- **Packet receipt.** The receive thread (`r_hub.c` `run_thread` L330–350) blocks in `read_one()` for one 376 B
  `r_remote_data`, then does `r->latest = data;`. **No receive time, count or order is kept.**
- **Device data.** `r_device_update_inputs()` marks every input active (or inactive if `latest->active` is false) and
  stamps **`timestamp = os_monotonic_get_ns()` at the update call**. The OpenXR `lastChangeTime` therefore reflects the
  update call, not the packet.
- **Pose.** `r_device_get_tracked_pose()` returns `latest->pose` for any requested time. Flags are VALID+TRACKED iff
  `latest->active`.
- **Where receive time and order can be kept.** Right after `r->latest = data` in the receive thread, which is
  where the patch adds it.

**Three distinct times.**

| Time | Where it exists |
|---|---|
| Packet receipt | driver receive thread; patched in |
| App read | the R11 A2 `acq_ns`, taken after the OpenVR call |
| Sensor observation | **not present anywhere**: the protocol has no source time, and the synthetic feeder has no sensor |

R15 measures packet receipt, never sensor observation.

**Source contract.** The synthetic feeder sends a full state packet every ≈ 10 ms, including when the hand is still:
a still hand is a periodic repeat of the same pose, and a stall is the absence of packets. A receive watchdog is
appropriate for this periodic contract only. **The same policy is not applicable to event-driven sources.**

## 2. Arms (all use the R11 A2 app copy and the same A2 check: app-read age ≤ 100 ms sim, valid, sequence increasing)

| Arm | Runtime | Extra information | Placement |
|---|---|---|---|
| S0 | original image `f3-xrizer-bgpump:0989a7f-v3` (R13 A2 reproduced) | none | app read → gate |
| S1 | `m12-monado-rxwd:045931d-v1` with `M12_RX_WATCHDOG_MS=100` | **standard receive watchdog in the driver.** If no packet arrives for > 100 ms (10 periods), the controller is reported exactly as `active = false` (pose flags 0, inputs inactive). The app (R11 A2 copy of `quest_teleop.py`) then sees pose-invalid and stops publishing. | runtime driver (a separate runtime variant, labelled) |
| S2 | the same patched image with `M12_RX_EVIDENCE=/tmp/m12_rx.txt` and no watchdog (poses unchanged) | the driver writes the latest receipt time and count to a file; the gate (A2S) additionally requires the latest receipt to be ≤ 100 ms old (container monotonic clock) at command receive | the same watchdog policy placed at the gate, as a separate evidence stream. It checks the latest state of that stream only and does **not** link a pose to a packet. |

**Patch.** `patch/apply_rx_watchdog.py`, applied in `patch/Dockerfile.rx_watchdog`. The diff is stored in the image
at `/src/m12_rx_watchdog.diff` (104 lines). The `monado-service` sha256 is `d26787ca…` (original `f211c735…`). With
neither variable set, behaviour equals the original driver.

**Clock domains.**

- The S1/S2 watchdog uses CLOCK_MONOTONIC inside the container. The driver and the gate share the clock, so no
  conversion is needed.
- The A2 app-read age uses the ROS sim clock (R11; normal apparent age 33–44 ms from clock propagation).

**Different thresholds, different things.** The watchdog threshold (100 ms of receive silence) and the app-age
threshold (100 ms) measure different things and are not interchangeable.

## 3. Conditions and schedule

| ID | Construction | Purpose |
|---|---|---|
| N_MOVE | normal motion | normal operation |
| N_STILL | still hand, periodic identical packets | false stops on a legitimate repeat |
| STALL15 | feeder silent 6.0–7.5 s, then resumes | short stall + recovery |
| STALL5 | feeder silent 6.0–11.0 s, then resumes | long stall + recovery |

3 arms × 4 conditions × 3 = **36 formal trials** (`schedule_wd.csv`; `Random(150 + rep)`; Latin arm rotation).

**Execution.** Each campaign extracts `git archive <freeze sha>` into `run_snapshot/<sha>/` (ignored). Before every
trial the snapshot is checked against the frozen hash lists.

## 4. Ground truth and measures (fixed)

- **Truth (as R11, hidden from all gates).** A message is `stale_source` iff the feeder sent no packet in the 100 ms
  before the bridge received the app message.
- **Measures:**
  - stale admitted / total;
  - fresh false blocks (all conditions; N_STILL in particular);
  - app messages inside the stall (S1 expected silent: "not generated" is distinguished from "blocked");
  - the last admitted command after stall start (detection/block latency);
  - the first admitted command after stall end (recovery latency);
  - the target jump between the last admitted command before the stall and the first after it.
- **Re-arm.** The A2 app copy inherits the original app's behaviour: it continues after pose-invalid without a new
  press and keeps its offset. Re-arm and re-anchor are **not** part of R15 (M39 covers them); the jump is reported.
- **Validity.** R11 rules; reruns at most 2; all attempts kept.

## 5. Interpretation limits (fixed)

- **Packet receipt, not physical sensing.** A watchdog success establishes freshness of **packet receipt** for a
  periodic source. It says nothing about the truth of physical sensing, which the synthetic source does not have.
- **Not generalized:** to real headset runtimes, event-driven sources or compromised components (S2 threat class
  out of scope).
- **Pre-flight** (raw `raw/preflight`, excluded; snapshot b3febe1). In all three runs: no false blocks; app
  read age ≤ 44 ms.

| Run | Result |
|---|---|
| PF1 S1 N_STILL | 270/270 admitted |
| PF2 S2 N_MOVE | 270/270 admitted; receipt age ≤ 10 ms |
| PF3 S1 STALL15 | app silent in the stall; last admit at +0.06 s; recovery 0.01 s after the stall end; resume target jump 47.9 mm |
