# P2 cause analysis: why the headless session stayed in READY, and what the `isActive=1` observation means (2026-10-02)

Supersedes the interpretation in `P2_RESULTS.md` (which is kept unchanged as the 2026-10-01 record).

## 1. What the extension requires

`XR_MND_headless`, `specification/sources/chapters/extensions/mnd/mnd_headless.adoc` at OpenXR-Docs
`release-1.1.63` (`5a82d45b`), revision 3 (2025-08-20):

- A headless session proceeds IDLE → READY.
- After `xrBeginSession` it proceeds to SYNCHRONIZED → VISIBLE → FOCUSED.
- "The application does not need to call `xrWaitFrame`, `xrBeginFrame`, or `xrEndFrame`."
- `primaryViewConfigurationType` must be ignored.

The installed header (`openxr.h`, loader 1.0.20) declares `XR_MND_headless_SPEC_VERSION 2`. The
revision-1/2 wording of the state-progression clause was **not retrieved**: NOT_VERIFIED. The revision
history lists rev 2 as "clarify xrWaitFrame is permitted" and rev 3 as a graphics-requirements
clarification. Neither entry says the state-progression rule was added.

## 2. Separation of causes

| Candidate cause | Finding | Evidence |
|---|---|---|
| Client | The calls were valid. The client enabled `XR_MND_headless`, created a session without a graphics binding (accepted as headless), and called `xrBeginSession` in READY (result 0). Polling events and `xrSyncActions` while running are valid. The v1.1 frame loop was optional and did not change the outcome. Passing `PRIMARY_STEREO` is harmless: it must be ignored. | `p2_client.c`; client logs `results/raw/P2/*/client.jsonl` |
| Installed Monado build | **Root cause.** Ubuntu `libopenxr1-monado 21.0.0+git2905.e26a272c1` corresponds to commit `e26a272c`, dated 2023-03-01. At that commit a headless session has `compositor = NULL` (`oxr_session.c` L856–860). `oxr_session_begin` only sets `has_begun` (L137–161). `oxr_session_poll` returns immediately when `compositor == NULL` (L233–238), so no SYNCHRONIZED/VISIBLE/FOCUSED transition can occur. Upstream fixed this in `d751468785c7` "st/oxr: Transition headless session to FOCUSED on begin session" (2023-12-11). At main `045931d` (2026-09-30) the headless branch sets `compositor_visible = compositor_focused = true` on begin ("Headless, pretend we got event from the compositor", `oxr_session.c` ≈L469–472). | sources under `references/upstream/monado` (e26a272c1) and main files fetched by commit (sha256 below) |
| Configuration | Not the cause. The `remote` driver, the null compositor and `monado-service` with an open stdin all started correctly. `monado-ctl -i/-f` acts on compositor-side client state, which a compositor-less headless session does not have, so a toggle cannot change it. | `service.log`, `ctl_list*.txt` |

## 3. Reinterpreting the `isActive=1` observation

| Point | Status |
|---|---|
| Observed on `e26a272c`: `xrSyncActions` returned `XR_SESSION_NOT_FOCUSED` while `xrGetActionStateBoolean` reported `isActive=1` with a live state | **EXPERIMENT_CONFIRMED, kept** |
| Was the call valid? | Yes. The session was running (begun), and getting action state is allowed in any running state. |
| Was the extension applied? | Yes. The session was created and treated as headless (`compositor = NULL` path). |
| Does it violate `input.adoc` L839–841 / L1344–1346? | **Yes, for this build.** The session was not focused, yet actions were active. But the not-focused state itself was only reachable because of the headless defect above. |
| Is it a property of Monado in general? | **No.** Upstream added "Handle the XR_SESSION_NOT_FOCUSED case for XRInput" (`bb6e8eb9`, 2023-11-15) and "Return if XR_SESSION_NOT_FOCUSED is not focused in xrSyncActions" (`246d42ed`, 2025-11-11). At main, `actions/oxr_input.c` ≈L1285–1291 zeroes the action state whenever `sess->state != FOCUSED`. |

**Corrected statement for the matrix (M2 trust condition).** *Runtime version* is a trust condition.
Distribution packages can lag the upstream fixes by years: this Ubuntu 24.04 package dates from
2023-03. An evidence path must pin and check the runtime build it relies on. Unconditional claims
about "Monado" are withdrawn.

## 4. Consequence for the feasibility study

- The headless failure is a **build-specific defect**. It is not evidence against an independent
  evidence path (kill criterion revised in `docs/05`).
- The next step is to build current Monado (main, pinned commit) unmodified. That build is expected
  to provide two things:
  - headless sessions that reach FOCUSED;
  - `libmonado` (the per-client state API behind `monado-ctl`), which is not in the Ubuntu package.
    The runtime is replaced by a newer upstream build, **not modified**.
- If a runtime patch ever becomes necessary, results with the original and with the patched runtime
  will be reported separately.
- A Vulkan-bound client is **not** needed for this question. It would be a workaround: it bypasses
  the headless path instead of fixing the build. It is kept only as a fallback, and would be labelled
  as such.

## Hashes of the fetched upstream files (main `045931d12f1c`)

- `src/xrt/state_trackers/oxr/oxr_session.c`
  `a409ef739dbf31933a5e69332682f0787f70fae1772343b9151196017a58aed9`
- `src/xrt/state_trackers/oxr/actions/oxr_input.c`
  `34a1bb1b3a161a788751d37ff51e7da81ca23c2eab4c126dfe04b5b915336038`
