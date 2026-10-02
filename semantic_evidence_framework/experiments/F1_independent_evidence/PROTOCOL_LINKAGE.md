# F1 linkage experiment — protocol (frozen 2026-10-02, before any measured run)

## 0. Status of what is tested

- **Mechanism validation with a stand-in app.** The "app" is our headless OpenXR client `sa_client`
  plus a command injector. **It is not one of the real apps**: none of the real apps reached a
  functional state on this host (`results/F1_CANDIDATE*.md`). Nothing here counts toward the "≥ 2
  unmodified real apps" go criterion.
- **Runtime:** unmodified Monado main `045931d`, headless, `remote` driver, in container
  `f1-monado-main:045931d`.
- **Security scope:** `SECURITY_SCOPE.md`. All claims are for **S1, an honest app**.

## 1. Evidence used

The runtime-side predicate is `INPUT_ACTIVE(c) := IO_ACTIVE ∧ ¬INPUTS_BLOCKED` from
`mnd_root_get_client_state` for the bound client `c = sa_main`.

- The service-side `SESSION_FOCUSED` flag is **not used**. The setup probe showed it stays 0 for
  headless clients, even though they report FOCUSED to themselves. This is recorded as a limitation:
  F1 tests input-activity evidence, not focus.
- **Lever:** `mnd_ctl io sa_main`, the runtime-enforced input deactivation (`toggle_client_io_active`).
  The probe showed the client then sees `isActive=0`.

## 2. Components (one container, separate processes)

| Role | Process | Notes |
|---|---|---|
| runtime | `monado-service` + `remote_feeder.py` (grip held) | trusted |
| app (stand-in) | `sa_client 16 sa_main` (+ `sa_client 16 sa_other` in K4) | app-side; its log gives the app-visible action state |
| app → ROS | `injector.py`: generates a command every 20 ms from 1.5 s to 12.0 s. Each command is a `PoseStamped`, `header.stamp` = generation time, `frame_id` = `seq=<n>;active=<app-visible isActive at generation>` (the self-report, used only by D_DIRECT). Delivery to `/xr/cmd` follows the case schedule (delay, reorder, replay). | — |
| app → ROS (modified-app variant) | `app_state.py` publishes `/xr/app_state` with the app-visible `isActive` at every `sa_client` sample. This models an app change that adds one stream. | used only by D_STREAM |
| collector | `mnd_collector 0.005` → FIFO → gate | trusted, out of the app process |
| gate | `gate.py`: evaluates **all policies on the same command stream** and logs per-policy decisions and decision times | trusted, at the consumer |

## 3. Policies (equal information within a source)

| ID | Evidence source | Rule |
|---|---|---|
| B0 | — | admit all (the existing app) |
| D_DIRECT | the app's self-report inside the command | admit iff `active=1` |
| D_STREAM | the app's state stream `/xr/app_state` | same rule as C_INTERVAL, evaluated on the app stream |
| C_ARRIVAL | runtime (collector) | admit iff the latest evidence is ≤ 50 ms old and `INPUT_ACTIVE(sa_main)` holds at arrival |
| C_INTERVAL | runtime | C_ARRIVAL **and** `INPUT_ACTIVE(sa_main)` holds in every evidence sample in [t_gen − δ, t_arr], with no evidence gap > 50 ms there, **and** t_arr − t_gen ≤ 200 ms **and** t_gen ≤ t_arr + 5 ms. δ = 10 ms. |
| C_ANY | runtime | admit iff *any* client has `INPUT_ACTIVE` at arrival (a wrong-binding baseline) |

**Clock.** Every process runs in one container on `CLOCK_REALTIME`. Command stamps and evidence share
that clock, so no offset is estimated. Uncertainty comes from the collector period (5 ms), the
`sa_client` period (about 10 ms), and runtime propagation (measured from the `mnd_ctl` call time).

## 4. Cases (3 runs each; 14 s per run)

W = [5.0, 7.0) s is the inactive window: `mnd_ctl io sa_main` at 5.0 s and again at 7.0 s.

| Case | Scenario |
|---|---|
| K1 normal | no W; delivery delay 10 ms |
| K2 late | W. Commands generated in [4.8, 7.2) get an extra 2.5 s of delivery delay; all others 10 ms. |
| K3a reorder | W; delays uniform in [0, 150] ms (seed 7), so commands reorder |
| K3b replay-after-loss | W. Commands generated in [2, 3) are re-sent unchanged (same stamp and seq) during [8, 9). |
| K3c replay, no loss | no W; the same replay |
| K4 cross-binding | W applied to `sa_main` only; `sa_other` stays active. Commands are bound to `sa_main`, 10 ms delay. |
| K5a evidence outage | no W. The collector is SIGSTOPped during [5.0, 6.0) and SIGCONTed after. |
| K5b evidence delay | W; the gate delays evidence processing by 30 ms |
| K6 premise | grip held 1–6 s and released at 6.0 s (inside W); W as above. This checks the runtime edge rule and replays the app log through ALVR's edge-only rule (no ROS scoring). |

## 5. Scoring (per command, per policy)

- **Truth source:** the app-visible `isActive` from the `sa_client` log. It is used only for scoring
  and is given to no policy.
- `inactive(t)`: the nearest `sa_client` sample to t has `isActive = 0`.
- **BOUNDARY:** a command whose t_gen or t_arr lies within 20 ms of a truth transition. It is
  reported separately and excluded from the counts below.
- **should_block** if any of these holds:
  - `inactive(t_gen)`;
  - `inactive(t_arr)`;
  - an inactive truth sample lies in (t_gen, t_arr);
  - t_arr − t_gen > 200 ms.

  Otherwise **should_admit**.
- **dangerous_pass** = admitted ∧ should_block. **false_block** = rejected ∧ should_admit.
  - K5a: commands blocked during the evidence outage count as false blocks. They are the expected
    fail-closed cost, and are reported per window.
- **Gate latency:** p50/p95 decision time per policy.
- **Evidence latency:** time from the `mnd_ctl` call to the transition seen (a) by the collector and
  (b) by `sa_client`.

## 6. Decision rules (fixed in advance)

1. **The independent path gives the S1 guarantee in this pilot** if all of these hold:
   - C_INTERVAL has 0 dangerous_pass (non-boundary) over K1–K5, all runs;
   - its false_block ≤ 1 % of should_admit commands, outside the K5a outage window;
   - K4 shows C_INTERVAL ≠ C_ANY.
2. **Comparison with app modification.** If D_STREAM achieves the same result, the guarantee itself
   is **not** a differentiator.
   - What remains to compare is the number of app-side modification sites (D_*: one per app, plus a
     message or topic change; C_*: 0), the deployment configuration, and the trust path (S2 is not
     claimed by either).
   - If D_DIRECT misses cases that D_STREAM or C_* catch, that is recorded as a limitation of
     self-reporting **inside the command**.
3. **No claim is made beyond:** headless input-activity evidence on one runtime build, the stand-in
   app, a single uid, no physical consumer. No real-app claim.
4. If C_INTERVAL has dangerous passes, they are attributed to a mechanism (poll period, gap, clock
   boundary) and reported. Thresholds are **not** retuned after outcomes.

## 7. Budget

9 cases × 3 runs = 27 runs at about 25 s each, sequential (about 12 min), plus a setup smoke of K1 only, which is excluded.
