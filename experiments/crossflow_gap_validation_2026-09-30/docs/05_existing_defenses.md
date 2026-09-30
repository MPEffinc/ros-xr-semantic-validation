# 05 — Strong Existing Defenses (Stage 5)

No new defense is built. This stage asks whether the strongest existing defenses, applied faithfully to
each flow of the Gate-1 deployment, can leave *cross-flow* leakage at all, and at what cost. Because there
is no real paired dataset (Stage 2), the answer rests on (i) a construction argument, (ii) literature
(`../literature/defense_baselines.md`), and (iii) one real-stack measurement of ROS 2 flow regularity.
None of it is an attacker-accuracy result on XR–ROS traffic.

## 1. Defense families considered

| # | Family | Representative (evidence) | What it hides | Per-flow or joint | Included? | Why |
|---|---|---|---|---|---|---|
| 1 | Encryption only | TLS/DTLS, SROS2 | content | per flow | yes (as B0) | leaves size/timing; K1/K2 show leakage |
| 2 | Fixed-size padding | Tang et al. ARES 2025 [A] (pad to x·100 B) | sizes | per flow | yes | timing untouched |
| 3 | Constant-rate / constant-interval (regularising) | BuFLO/CS-BuFLO/Tamaraw (via FRONT tables [A]); Tang "latency-aware traffic modulation" [A]; Maybenot state machines [C] | sizes **and** timing | per flow or tunnel | **yes — the strongest per-flow defense** | makes the observable schedule content-independent |
| 4 | Dummy traffic, zero-delay | FRONT/GLUE [A], WTF-PAD | partial timing | per flow | yes | cheap; correlation known to survive (DeepCoFFEA [A]) |
| 5 | Segmentation / splitting | TrafficSliver [not read] | per-path volume | multi-path | no | needs multi-path; not in any audited XR–ROS stack |
| 6 | Latency-aware modulation | Tang ARES 2025 [A] | sizes+timing under a latency bound | per flow | yes (= family 3 with deadline) | explicitly designed for robot control |
| 7 | Strong WF defenses with generation | Surakav [A], Palette [A], RegulaTor [A] | web-page traces | per flow | no | built for request/response web loads, not periodic control/media |
| 8 | DP shaping | NetShaper USENIX'24 [A] (single DP-shaped QUIC tunnel, T ≥ 10 ms) | bounded leakage (ε) | **joint (tunnel)** | yes | strongest principled joint shaper; code public |
| 9 | Multi-flow interleaving / mixing | Minos ATC'25 [A] (< 20 % attack acc. with ≥ 5 flows, 0–12 % bw); VPN aggregation (PingPong [A]; Apthorpe [A]) | per-flow separability | **joint** | yes | removes flow identity |
| 10 | Scheduler + per-flow defense | CBR multiplexing of haptics+video (Cizmeci et al. [A], QoS only); TSN (no traffic-analysis evaluation found) | timing incidentally | joint | noted | no security evaluation exists |

## 2. Construction argument (why the strongest per-flow defense leaves no cross-flow channel)

Let the observer see traces O = (O₁,…,O_k), one per protected flow. A per-flow **regularising** defense
(family 3/6) emits flow *i* on a schedule Sᵢ — packet times and sizes — that depends only on public
parameters and the session start/end times, provided the application demand never exceeds the scheduled
capacity within the latency budget. Then every Oᵢ is a function of (parameters, session boundaries) alone,
and so is the joint O. Hence

  I(task ; O₁,…,O_k) = I(task ; session boundaries),

for **any** attacker, including one that exploits lags, burst alignment or ordering between flows. Pairwise
relations between constant schedules carry no task information. This is a property of the construction,
not a measured result (evidence D, but elementary).

The equality can break only through channels the construction assumes away. Each has a known remedy:

| Residual channel | Existing remedy |
|---|---|
| session on/off correlated with task | keep the session and the shapers running across tasks (standard session-level padding) |
| demand exceeding the schedule (queue growth, drops, rate switches in CS-BuFLO-style adaptive variants) | provision rate ≥ peak demand within the latency budget; avoid adaptive rate switches |
| content-triggered retransmission (TCP) | UDP / DDS best-effort, or fixed-schedule reliability |
| non-network side channels (EM, VReaves 2025 [A]) | out of scope |

**Consequence.** Under the strongest per-flow defense the hypothesis ("per-flow protection still leaks via
cross-flow correlation") is false by construction. It can only hold for *weaker*, cheaper defenses
(families 2, 4, per-flow DP):
- **Zero-delay padding (FRONT, WTF-PAD).** Surviving correlation is already shown by DeepCoFFEA (TPR > 50 % at FPR 10⁻⁵ under WTF-PAD/obfs4) — collision K4.
- **Per-flow DP.** Leakage about a secret shared by several flows is bounded by composition of the per-flow budgets. This is our inference (D); NetShaper itself avoids the question by shaping all flows in one tunnel.

## 3. Cost of the strongest per-flow defense in XR–ROS teleoperation

**ROS command/feedback flows — measured.** Real ROS 2 Humble, FastDDS default, two containers on a Docker bridge. Content was synthetic random on purpose: the question is an implementation property. Details: `../results/stage5_ros_size_probe.txt`; manifest row `ros_size_probe_001` (UPSTREAM); script `../scripts/ros_flow_size_probe.py`.

| Flow (teleop-style message) | Rate | Wire sizes (20 s) | Inter-arrival |
|---|---|---|---|
| `PoseArray` (2 poses, like `xr_teleop/ee_poses`) | 60.1 /s | 398 B × 1,135, 430 B × 4 | 16.67 ms ± 0.05 ms |
| `JointState` (12 joints, like `finger_joints`) | 60.1 /s | 254 B × 1,137, 286 B × 2 | 16.67 ms ± 0.03 ms |

- The rare +32 B packets are consistent with an RTPS reliability submessage piggy-backed on a data packet (inference D; packets not decoded). They are periodic metadata, not content.
- Random content therefore gave constant sizes and a clock-driven rate. Isaac ROS Teleop's own node publishes at a fixed 60 Hz loop with fixed-shape messages (`teleop_ros2_node.py`, launch `rate_hz` 60).
- Making such flows strictly constant-rate costs only padding to the largest size (≈ 8 %) plus suppressing on/off events. Example: `head_pose` is not published while tracking is invalid (IsaacTeleop@de761a03 `examples/teleop_ros2/python/messages.py:403-404`), and that on/off pattern is itself a signal to pad.
- Event-driven ROS topics (TF bursts, action feedback, compressed camera images) would need padding up to one period of added latency. That is a bounded, known trade-off.

**XR media flow — not measurable here.**
- VBR video at 100–200 Mbps with a 20–30 ms pose-to-frame budget. Regularising it costs roughly peak/mean bandwidth with no added delay if provisioned at peak.
- CBR encoder modes are the standard way to do this. Whether CloudXR exposes CBR is NOT_VERIFIED.
- Tang et al.'s "478 times bandwidth overhead" / "not practical" (ARES 2025 §7.2) concerns latency-bounded constant-rate for 1 kHz robot control, whose native traffic is far from periodic. That does not match the fixed 60 Hz teleop streams measured above.

## 4. Stage 5 conclusion

- **The strongest existing per-flow defense closes the cross-flow channel by construction.** It is regularising constant-rate / constant-size, applied to every flow with session-level padding. Its cost is small for the ROS flows (measured) and a known bandwidth trade-off for the media flow.
- **Joint defenses already exist.** NetShaper (one DP tunnel) and Minos (mixing) handle the cross-flow case explicitly.
- **What remains is not a cross-flow methodology problem.** It is the cost/latency tuning of these known mechanisms, which Tang et al. already identify as open: "a pressing need for … more sophisticated low-delay defense strategies". That matches the excluded category "단순 latency-aware traffic padding".

Defense-aware attacker retraining, latency/jitter, task success and completion-time measurements
(required by the brief) are **NOT_RUN**: they need the real paired dataset that Stage 2 could not produce.
