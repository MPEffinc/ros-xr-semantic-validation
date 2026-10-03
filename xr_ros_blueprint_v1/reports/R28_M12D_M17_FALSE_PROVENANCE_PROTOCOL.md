# R28 — M12D/M17: false provenance and command derivation (protocol; frozen before formal runs)

**Protection condition (declared first).** *Only commands derived from an allowed source sample, through the trusted
declared mapping, are executed.*

**Attacker.** A-app (A04): the app holds its normal permissions and chooses every field it sends, including stamps,
seq, session, source time, validity and target. Signed or authenticated delivery from this app would not make these
claims true. That is outside what authentication guarantees, and it is not counted as a failure of authentication.

**Level.** An isolated synthetic source / command experiment: no robot, no runtime, no Servo. All targets stay within
±0.05 m of the anchor; the qualified range is not exceeded.

## 1. Components (`M17_derive/harness`)

| Component | Trust | Role |
|---|---|---|
| `source.py` | trusted | `SourceSample` at 100 Hz (session `s1`, seq from 1, `header.stamp` = sample time, grip from 1.0 s, valid). Hand: x 0.05 m at 0.5 Hz, y 0.02 m at 0.2 Hz. Also the robot-state anchor (`/m17/robot_ee`, 50 Hz). |
| `common.py` | frozen specification | declared mapping `target = anchor + K·(hand − hand_ref)`, K = 1; τ = 100 ms; tolerance 1 mm; window 5.0–6.0 s |
| `app.py` | **untrusted** | maps every second sample after engage and publishes `ProvCommand` with its own provenance fields. In the window it applies the condition. It writes the ground-truth label of each command to the harness truth log, which no gate reads. |
| `gate.py` AP | arm 1 | **app-provenance gate**: standard freshness/seq/validity practice on the app's fields (valid; stamp age ≤ τ; `src_time` age ≤ τ; seq increasing per session) |
| `gate.py` TV | arm 2 | **trusted verifier outside the app**: subscribes the source and the robot state itself; owns engage (its own first grip sample) and the anchor; looks up the claimed (session, seq) in its own buffer (bounded wait 20 ms); requires the source-marked valid flag, its own receipt age ≤ τ and an increasing seq; recomputes the declared mapping and admits iff the target matches within 1 mm |

**Independence of TV from the app.**

- The source stream, the robot-state anchor, the engage event and the mapping specification all come from processes
  or files the app does not write.
- The only app-supplied item TV uses is the **claimed sample identifier**, which it verifies against its own buffer.

**Premise not enforced in these runs:**

- the app cannot publish `/m17/source` or `/m17/robot_ee`, or reach the verifier process. Topic-level enforcement of
  this kind is R27; it is not active here.
- On the real Monado path, an independent source tap would go through the unauthenticated runtime IPC (A04 §3).
  **This experiment does not establish that premise.**

**Verify vs. generate.**

- TV verifies the app's proposal.
- A trusted mapper that **generates** commands itself would ignore the app's proposal. TV logs that shadow target
  (`shadow_direct`) for comparison.
- Both need the same independent state. Generation also removes the app's influence on content, including legitimate
  app features (see the smoothing probe below).

## 2. Conditions (window 5.0–6.0 s; honest outside the window)

| ID | App behaviour in the window |
|---|---|
| NORMAL | honest |
| FAKE_TARGET | an arbitrary target (0.03 m Lissajous around the anchor) with the provenance of the latest real sample and fresh stamps |
| REWRITE_STALE | the target mapped from the sample 1.0 s older, with provenance rewritten to the latest real sample and fresh stamps |
| WRONG_MAP | the latest real sample and its true provenance; the target from a wrong calibration (+0.020 m on y) |

A forged command whose target lies within 1 mm of the honest target is labelled `forged_equivalent` and reported
separately. 2 arms × 4 × 3 = **24 formal trials** (`schedule_m17.csv`).

## 3. Measures (`analysis/analyze_m17.py`)

- normal: admitted / total (false blocks);
- forged: admitted / total;
- `forged_equivalent` separately;
- block reasons;
- decision latency (median / p95 / max);
- undecided commands.

Invalid: setup failure, fewer than 300 commands, or no decisions. Reruns: invalid only, at most 2.

## 4. Pre-flight (excluded; snapshot 795377f; 08:24–08:26)

- **First attempt (snapshot 7f6a177).** The app process did not exit, so each run hit the 300 s container timeout.
  - The app now exits on its own timer.
  - The four raw directories from that attempt (PF1–PF4, timed out) were **deleted** while being cleaned up.
  - Their data were never analysed. This deletion is recorded here.

| Run | Normal admitted | Forged admitted | Notes |
|---|---|---|---|
| PF1 TV FAKE_TARGET | 350/350 | **0/50** (mapping_mismatch) | forged deviation 6.8–79.4 mm |
| PF2 AP REWRITE_STALE | 350/350 | **50/50** | deviation 19.3–102.7 mm |
| PF3 TV NORMAL | 400/400 | — | latency median 0.007 ms, max 0.076 ms |
| PF4 TV SMOOTH_PROBE (probe only) | **21/400** | — | a **legitimate** app feature (EMA α = 0.3) was blocked 379 times: verification requires the app's mapping to be reproducible by the verifier |
| PF5 TV WRONG_MAP | 350/350 | **0/50** | deviation 20.0 mm |

No rule changed after the pre-flight.

## 5. Limits

- Synthetic source and command level; one mapping (translation, K = 1).
- **TV residuals:**
  - within τ, the app can still choose **which** recent sample to cite (selective replay, bounded by τ and
    monotonic seq);
  - it can withhold commands, which is the safe direction;
  - it cannot alter the content beyond the tolerance.
- The TCB of TV covers:
  - the source and robot-state processes;
  - the mapping specification and the verifier;
  - the transport and the topic permissions protecting them;
  - on a real XR path, the runtime/driver (A-rt) and its control interface (M18).
- **Not a full S2 defense:** runtime control bypasses (A04 §3) and action/service paths (A04 §7) remain.
