# R23 — ChatGPT review of R19–R22 (2026-10-04)

Repository reference: `41a9fc1ae9543e393fb336136e48afa4e5040192`. This is a review of the reports, protocols and DB, not a new experiment or an independent inspection of host raw files.

## Supported findings and scope

| Result | What the evidence supports | Boundary |
|---|---|---|
| R19 | Keeping packet receipt time lets a standard watchdog detect silence for the declared 10 ms periodic synthetic source | Packet receipt is not sensing. Both S1 and S2 use a runtime modification. The gate arm has no sample-specific binding. Source restoration retains 47.9/67.9 mm target jumps. |
| R20 | Real Docker_Teleop receiver code loses receipt/order provenance; typed preservation plus producer seq/session permits known checks | Backend/component with synthetic producer, not a second real XR frontend. Requires producer changes not supplied by the current Unity sender. |
| R21 | In the configured command-level task, represented-at tf is correct for a historical world target, while latest tf is correct for following the current frame | Scripted translation-only frame and generation-time representation. No admitted-delay effect was measured. |
| R22 | The existing mux blocks the sampled delayed trajectory for paths routed through it | The injected target was near the stopped pose, so CUR displacement of hold produced 0 mm observed motion. Direct topic writes, action and re-arm remain outside the test. |

## Interpretation cautions

- R19's 60–67 ms values describe the last admitted command after the stall began. They are not a direct measurement of the instant a 100 ms monotonic watchdog expired. Alarm time, first suppression time and last successful admission are distinct.
- R20's 13/14591 false-block count is outside the designed missing-provenance window. The separate 506 fresh-message blocks under fail-closed must accompany it when reporting applicability to an unmodified frontend. The time-based ground-truth edge remains counted and should not be called a proven semantic false block without a packet binding.
- R21's maximum 81 mm is converted command target error, not robot travel or injury. The restamp result establishes the importance of retaining representation time for the H task.
- R21's 80 ms delay exceeded the available 100 ms age budget once baseline age was included. The 36 valid trials do not establish the intended admitted-delay result. Keep the design-premise failure and test a separately frozen condition.
- Accurate conversion of an old representation does not itself establish freshness or continuing authorization. The declaration must distinguish transport age, representation time, observation age and any goal/command lease.
- M7's DB evidence label includes the real app and Gazebo, but its experiment is configured and evaluated at command level. Do not treat it as an original frontend incident or a judged physical outcome.
- R19 arm S2 is an experimental gate placement, not a defense result against the S2 compromised-component threat class.

## Research judgment

The repeated missing requirements now include receipt/observation/read/representation times, source sequence/session, neutral-versus-motion meaning, task mode and final writer mediation. This supports a minimum contract or conformance-study question. It does not establish that a shared implementation reduces total adapter, source, deployment and trust costs.

A standard known method at the consumer is not sufficient evidence that all prerequisites exist in a real deployment. Likewise, implementation gaps and information-path requirements remain valid matrix data even without a new decision algorithm.

Avoid continuing to tune honest-app stop/freshness cases indefinitely. After small checks of the admitted-delay and distant-late-message questions, move toward M12D/M17/M18/M19: untrusted application metadata, trusted mapping/evidence, runtime management permissions and execution bypass. Authentication, semantic correctness and complete mediation are separate requirements.

The strongest existing comparator for a command-derivation claim should include a trusted mapper or verifier outside the app, with declared source, calibration and task-state assumptions. A signature from a compromised app does not make its claims true. A trusted mapper is also a known baseline, not automatically a novel system.

The current roadmap's two heterogeneous real-path requirement remains for a broad deployment/system claim. Component comparisons and contract specification can be developed as preliminary evidence, while the second real frontend is blocked.

## Follow-up scope

The next executable prompt is supplied separately. This document records interpretation and research direction; it does not authorize execution by itself.
