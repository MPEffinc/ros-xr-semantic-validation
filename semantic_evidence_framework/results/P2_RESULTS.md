> **2026-10-02 correction.** The cause and meaning below are superseded by `P2_CAUSE_ANALYSIS.md`.
> The READY state comes from a 2023-03 Monado build defect, fixed upstream on 2023-12-11. The `isActive=1` observation is
> specific to that build, not a general Monado or spec-conformance property. The text below is kept as the original record.

# P2 results — Monado runtime check (2026-10-01): BLOCKED_ENV for the main question, one runtime observation

- **Protocol:** `experiments/P2_monado_runtime_semantics/PROTOCOL.md`. v1.0 was frozen at `4e1a994`
  and amended to v1.1 at `269613f` after run A1.
- **Raw data:** `results/raw/P2/` (ignored). sha256 per file: `results/P2_RAW_SHA256.txt`.
- **Runtime:** Monado 21.0.0+git2905.e26a272c1, null compositor, `remote` driver (Remote HMD and
  Remote Left/Right Controller, Index profile). The client was headless (`XR_MND_headless`).

## Main question: NOT ANSWERED (BLOCKED_ENV)

The headless session never left READY in any run (A1, v1.1 A/B/F, diagnostic):

- It went IDLE → READY, and `xrBeginSession` returned success.
- With the v1.1 frame loop, `xrWaitFrame` returned `XR_SUCCESS`, but every `xrBeginFrame` failed with
  `XR_ERROR_CALL_ORDER_INVALID` ("without xrWaitFrame").
- The Monado session state machine is driven by compositor visibility and focus events
  (`oxr_session.c` L253–274 @ e26a272c1). A headless session has none, so it never reaches FOCUSED.
- `monado-ctl -i` / `-f` had no visible effect: `io: 1`, `foc: 0` throughout.

The premise of H-A1 on a real runtime therefore **remains NOT_VERIFIED**: does an inactive action
suppress `changedSinceLastSync` across a focus or input transition?

**Next step.** Use a non-headless client with a Vulkan graphics binding on the null compositor
(estimated at about 150 more lines of C), or the Monado test suite's own client.

## Observation kept (run A1, EXPERIMENT_CONFIRMED on this runtime build)

While not focused (state READY, `xrSyncActions` = `XR_SESSION_NOT_FOCUSED` (8)), the runtime reported
the boolean action as **`isActive=1` with a live `currentState`**. It followed the remote `a/click`:
1,287 samples with state 0 and 497 with state 1. The v1.1 runs reproduced this in A, B and F.

| Source check | Result |
|---|---|
| Action update | `oxr_action_sync_data` updates every attachment regardless of focus. Only the return code reflects it (`oxr_session_success_focused_result`; `oxr_input.c` L1628–1646, `oxr_objects.h` L1678–1685). |
| Edge suppression | `oxr_action_attachment_update` does implement the spec's edge suppression after inactivity: `changed=false` when it was previously inactive (`oxr_input.c` ≈L1218–1232). |
| Search for a focus check | "focus" was searched in `oxr_input.c` / `oxr_api_action.c` at e26a272c1 and in the action files at main `045931d` (2026-09-30). Result: NOT_FOUND_IN_SEARCH. |

**Meaning for the matrix: a trust condition on the evidence source.**

- This build does not satisfy `input.adoc` L839–841 / L1344–1346 for action activity while unfocused.
- An evidence consumer that relies on `isActive` alone would treat unfocused input as active here. The
  `xrSyncActions` result code is the field that does carry the focus fact.
- Any runtime-side evidence path therefore has to state which runtime fields it trusts, and verify
  conformance per runtime.
- This is reported as an observation on one runtime build in the READY state. It is not a claim about
  FOCUSED→unfocused transitions, which were not reached, or about other runtimes. Whether an upstream
  issue already exists: **not searched**.
