# F1 linkage results — runtime-side input-activity evidence linked to ROS commands (2026-10-02)

- **Protocol:** `experiments/F1_independent_evidence/PROTOCOL_LINKAGE.md`, frozen at commit `d25c64e`.
  Security scope: `SECURITY_SCOPE.md`.
- **Raw data:** `results/raw/F1/linkage_formal/` (ignored). Per-file sha256 is in
  `results/F1_RAW_SHA256.txt` (422 files, smokes and probes included). Runner log:
  `results/F1_linkage_runner.log`.
- **Execution:** 27/27 runs, rc 0. Host load average was about 0.5–1.
- **Analysis:** frozen `analyze_linkage.py` → `linkage_summary.json`
  (sha256 `76094529…02cb9`). K6: `k6_premise.py` → `k6_premise_result.jsonl` (sha256 `b0233908…c434c`).
- **Labels:** EXPERIMENT_CONFIRMED for a **stand-in app** on **Monado main `045931d`** (headless,
  `remote` driver), one uid, no physical consumer. **Not a real-app result.**

## 1. What was observed (runtime side, out of the app process)

| Observation | Result |
|---|---|
| Runtime-side input-activity evidence | `IO_ACTIVE ∧ ¬INPUTS_BLOCKED` from libmonado. It tracked the app-visible `isActive` across every runtime-enforced deactivation. |
| Propagation from the `mnd_ctl` call (36 transitions) | Seen by the collector after a median of 11.1 ms (max 53.5); seen by the app after a median of 12.9 ms (max 58.6). The two paths are within about 10 ms of each other. The roughly 50 ms outliers appear on both paths, so they are runtime-side. |
| Focus | **Not observable** for headless clients: the service flag stays 0 while the client is FOCUSED (setup probe). F1 therefore covers input activity, not focus. |
| **Premise of H-A1 on a real runtime (K6, 3/3)** | The grip was released at 6.0 s inside the inactive window (5–7 s). At reactivation the runtime reports `isActive=1, current=0, changed=0`, so there is no release edge (spec `input.adoc` L857–866 is honoured). Replaying the app-visible states through ALVR's edge-only forwarding rule: the only forwarded edge is the press at about 1.0 s, so **the forwarded deadman stays "pressed" until the end while the runtime state is released**. The P1 assumption is now confirmed on Monado; Meta's Quest runtime remains NOT_VERIFIED. |

## 2. What was linked, and how

- **Command ↔ evidence linkage is by time on one host clock** (CLOCK_REALTIME in one container).
  The command `header.stamp` is the generation time; the evidence is sampled every 5 ms by the
  collector.
- **Binding** command topic ↔ runtime client (`sa_main`) is set by deployment configuration. It is not
  attested (`SECURITY_SCOPE.md`).
- **There is no per-sample provenance.** The command does not carry the OpenXR sample it came from,
  so the gate checks *runtime state over the command's lifetime* [t_gen − 10 ms, t_arr]. It does not
  check that the command was derived from a particular active sample.

## 3. Which commands were blocked (non-boundary; dangerous passes / should-block, all 3 runs)

| Case | B0 (existing app) | D_DIRECT (self-report in command) | D_STREAM (app state stream) | C_ARRIVAL (runtime, at arrival) | **C_INTERVAL (runtime, interval)** | C_ANY (wrong binding) |
|---|---|---|---|---|---|---|
| K2 generated inactive, arrives after reactivation | 348/348 | 53/348 | 0/348 | 348/348 | **0/348** | 348/348 |
| K3a delay/reorder 0–150 ms | 299/299 | 12/299 | 0/299 | 6/299 | **0/299** | 299/299 |
| K3b replay after an inactive interval | 444/444 | 150/444 | 0/444 | 150/444 | **0/444** | 444/444 |
| K3c replay of stale commands, no loss | 150/150 | 150/150 | 0/150 | 150/150 | **0/150** | 150/150 |
| K4 another client active | 291/291 | 0/291 | 0/291 | 0/291 | **0/291** | 291/291 |
| K5b evidence delayed 30 ms | 294/294 | 0/294 | 0/294 | 0/294 | **0/294** | 294/294 |
| K6 release inside inactive window | 291/291 | 0/291 | 0/291 | 0/291 | **0/291** | 291/291 |

**False blocks** (false blocks / should-admit, all cases):

- **0** for every policy, except under K5a, the collector outage. There C_INTERVAL blocked 147 of 1,578
  and C_ARRIVAL/C_ANY 144, **all inside the outage window** (fail-closed). D_STREAM had 0 under K5a,
  because its evidence path was not interrupted.
- **K1 normal:** 0/1,578 false blocks for every policy.

**Boundary commands** (within 20 ms of a truth transition) are excluded above and listed here: 12–22
per case. C_INTERVAL admitted 0–8 of them per case (K3b 4, K4 6, K5b 8, K6 5). **The guarantee holds
only outside a ±20 ms band** around transitions, and that band should be widened by the observed
propagation outliers (about 50 ms).

**Gate decision cost** (p50 / p95):

| Policy | p50 | p95 |
|---|---|---|
| C_INTERVAL | 1.6 µs | 2.8 µs |
| C_ARRIVAL | 0.9 µs | 1.5 µs |
| D_STREAM | 4.3 µs | 6.7 µs |
| B0 | 0.4 µs | 0.4 µs |

The dominant added latency is evidence propagation (about 11 ms median), not the decision.

**Decision rule 1 (§6) is met.** C_INTERVAL had 0 dangerous passes over K1–K5. Its false blocks were
0 outside the outage, and K4 separates it from C_ANY.

## 4. Comparison under the same guarantee (§6 rule 2)

| | Existing app (B0) | Direct delivery inside the command (D_DIRECT) | App state stream (D_STREAM) | Independent runtime path (C_INTERVAL) |
|---|---|---|---|---|
| Guarantee reached in K1–K6 (S1) | none | partial: misses late, replayed and stale commands, because generation-time self-report cannot express arrival-time state or lifetime | **full** (same as C_INTERVAL) | **full** |
| App-side modification sites | 0 | read `isActive` + 1 message field + sender change, **per app** | read `isActive` + 1 new publisher/topic, **per app** | **0** |
| Feasible for the closed apps audited (Quest2ROS2, OpenArmX, the PickNik host) | — | no (closed) | no (closed) | only if the app runs on a runtime whose service exposes client IO state. None of the 6 audited apps did on this host. |
| Deployment configuration | — | consumer check | gate + topic | collector + gate + **binding config** (topic ↔ runtime client) |
| Runtime modification | — | — | — | none (Monado main unmodified; a newer build than the Ubuntu package was required) |
| Evidence-path failure behaviour | — | — | independent of the runtime path | fail-closed blocks during an outage (147 false blocks in 1 s); a local client can crash the service (F1 bring-up §1) |
| Trust against a compromised app (S2) | — | none (self-report) | none (self-report) | **none in this pilot**: libmonado control calls are unauthenticated on the app's socket, and client identity is self-reported |

**Interpretation.**

- For an honest app, the **guarantee is not a differentiator**: D_STREAM matches C_INTERVAL exactly.
- The independent path differs in two ways:
  - **(a) zero app-side changes.** It needs only runtime-side observability, which the app does not
    have to provide.
  - **(b) the evidence source is the runtime's state, not the app's.** This would matter against S2,
    but only if the control interface were authenticated. It is not, in Monado main.
- Self-report **inside the command** (D_DIRECT) is structurally weaker than any state stream. It
  cannot block commands that become inapplicable after generation (K2/K3).

## 5. What is not guaranteed

- **Command provenance.** There is no sample-level linkage. A command stamped inside an active
  interval passes even if it was not derived from an active sample (S1 mistakes outside the tested
  ones, or any S2 behaviour).
- **The ±20 ms band** around transitions, plus about 50 ms runtime propagation outliers.
- **Focus** (not observable for headless clients) and tracking state (not tested). Origin/anchor
  changes are not tested: app-internal calibration is not observable through the runtime, and runtime
  reference-space offsets (`mnd_root_get_reference_space_offset`) were not exercised.
- **Real apps.** None ran functionally on this host (`F1_CANDIDATE1_BRINGUP.md`,
  `F1_CANDIDATE2_ISAACTELEOP.md`).
- **S2.** Not defended (`SECURITY_SCOPE.md`).
- **Physical consumer effect.** Not measured here; see P1b for the execution-pipeline residual.
