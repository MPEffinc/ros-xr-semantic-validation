# R30 — M12D/M17 false provenance and command derivation: results (R28; 24/24 valid, 2026-10-04)

| | |
|---|---|
| Protocol | R28, frozen ce74cfe; `git archive` snapshot with per-trial hash checks |
| Raw data | `experiments/M17_derive/raw/` (ignored, 9.6 MB, 263 files); sha256 in `results/M17_RAW_SHA256.txt`; measures in `results/m17_trials.json` |
| Level | isolated synthetic source / command level, A-app attacker; topic permissions protecting the source and the verifier are a premise, not enforced in these runs |

## Results (3 trials per cell, summed; the window holds 50 forged commands per trial)

| Condition | AP: normal admitted | AP: forged admitted | TV: normal admitted | TV: forged admitted |
|---|---|---|---|---|
| NORMAL | 1200/1200 | — | 1200/1200 | — |
| FAKE_TARGET (arbitrary target, real latest provenance; deviation 6.8–79.4 mm) | 1050/1050 | **150/150** | 1050/1050 | **0/150** (mapping_mismatch) |
| REWRITE_STALE (1 s old input, rewritten provenance; 18.9–102.7 mm) | 1050/1050 | **150/150** | 1050/1050 | **0/150** |
| WRONG_MAP (true provenance, +20 mm calibration error) | 1050/1050 | **150/150** | 1050/1050 | **0/150** |

**Other measures:**

- No forged command fell within 1 mm of the honest target (`forged_equivalent` = 0).
- No command was left undecided.
- Decision latency: p95 ≤ 0.023 ms in both arms; maximum 0.094 ms (AP) and 1.5 ms (TV, one bounded wait).
- **Pre-flight probe (excluded):** a legitimate app feature (EMA smoothing, α = 0.3) under TV admitted 21/400
  honest commands.

## Reading

**AP: provenance supplied by the app protects nothing against A-app.**

- A fresh stamp, an increasing seq, a valid flag and a fresh source time were all present on 450/450 forged commands,
  because the app writes them. This is the expected outcome of the A-app threat model.
- It is not a failure of freshness checking or of authentication. These checks answer "is this message from an
  honest app recent and ordered?", not "is it true?".

**TV: verification outside the app against independently received source data blocked every forged command, with no
false blocks.** This is a known baseline: a trusted mapper/verifier.

What it needs:

| Need | In this experiment |
|---|---|
| an independent source stream | its own subscription |
| the declared mapping | frozen specification |
| task and calibration state the verifier owns | engage from the source, anchor from trusted robot state |
| a claimed sample identifier to bind command to sample | the app's (session, seq) |

What it costs:

- **The app's mapping must be reproducible.** Legitimate app-side features (smoothing, retargeting, UI-driven
  re-anchoring) must move into the verifier's TCB or be given up. The smoothing probe lost 95 % of commands.
- A trusted mapper that **generates** commands is equivalent in TCB and removes the app's content entirely.

What remains (not tested):

- the app can choose which recent sample to cite within τ (selective replay);
- it can withhold commands;
- forged source data under A-rt, or the unauthenticated driver port under A-net;
- runtime control over the IPC socket (M18, A04);
- action and service paths (A04 §7).

**Classification.**

- **M17 (command derivation under A-app)** is solved, at synthetic command level, by the existing trusted-verifier
  baseline. This holds only where a source stream independent of the app and a reproducible mapping exist.
- On the real Monado/xrizer path these premises are **not available unmodified**: there is no sample identifier in
  the legacy API, and the only independent tap would use the unauthenticated runtime IPC.
- **M12D** follows the same rule: app-supplied provenance must be treated as a claim. The check it needs is
  independent evidence, not stronger authentication of the app.
