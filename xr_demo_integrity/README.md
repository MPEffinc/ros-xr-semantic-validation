# xr_demo_integrity — Research Workspace

Working title (a candidate to be refuted or confirmed, not a claim):
**Integrity of XR-Teleoperation Demonstrations for Robot Learning**
(XR 원격조작으로 수집되는 로봇 학습 데이터의 무결성)

Candidate question:

> In a real XR→ROS demonstration-collection system, can a component with *limited, actually existing*
> write authority change the meaning of the recorded learning data; can existing data-validation
> methods detect or repair that change; and does it affect the behaviour of a policy trained on it?

If existing techniques already solve the problem, no new framework is developed. The candidate is
not assumed to survive.

Started 2026-09-30 from `main@a619e23d208a55c7c75cbaee66d954b6d123fc34`. Literature cut-off date: 2026-09-30.

## Evidence labels

| Label | Meaning |
|---|---|
| `SOURCE_CONFIRMED` | Read in source code / paper text at a pinned revision (path, lines or section given). |
| `AUTHOR_STATED_LIMITATION` | A limitation, discussion item or future-work item written by the authors (section/page given). |
| `DERIVED_HYPOTHESIS` | Our conjecture derived from sources; not yet tested. |
| `EXPERIMENT_CONFIRMED` | Observed in an experiment run **in this workspace**, with inputs, outputs and hashes. |
| `NOT_VERIFIED` | Could not be checked (no access, no artifact, not run). |
| `PRIOR_INTERNAL` | Result from a closed study in this repository; background only, never re-labelled as new. |

Testbed provenance classes: `UPSTREAM_NATIVE`, `UPSTREAM_WITH_DOCUMENTED_INTEGRATION`, `SYNTHETIC_MODEL`.
Trial outcomes: `PASS` / `FAIL` / `UNKNOWN` / `NOT_RUN`.

## Closed studies in this repository (read-only for this workspace)

| Study | Location | Verdict |
|---|---|---|
| A. Semantic validation of XR teleop command streams (S1–S5) | `../Deprecated/semantic_validation/results/S5_EVIDENCE_AUDIT.md` | NO_METHOD_GAP for the tested conditions |
| B. Authorization Continuity / XR2Act (Aug 2026) | `../Deprecated/AUTHORIZATION_CONTINUITY_RESULTS.md`, `../Deprecated/XR2ACT_DECISIVE_RESULTS.md` | WEAK / CASE-STUDY ONLY (HORUS adapter defects) |
| C. Authority Continuity (Sep 2026) | `../authority_continuity/hypotheses/GO_NO_GO.md` | IMPLEMENTATION_GAP_ONLY |

Overlap with these studies is recorded in `RESEARCH_PLAN.md` §2. Nothing in `../Deprecated/` or
`../authority_continuity/` is modified by this workspace.

## Layout

| Path | Content |
|---|---|
| `literature/` | Verified key papers, citation edges, author-stated limitations, source ledger |
| `systems/` | Upstream inventory (pinned SHAs), dataflow, trust boundaries, line-level source audit |
| `hypotheses/` | Threat model, research questions, go/no-go gates |
| `experiments/` | Frozen protocol, baselines, harness, tests |
| `results/` | Summaries and hashes (raw outputs stay local in `results/raw/`, git-ignored) |
| `scripts/` | Reproduction scripts (clone-at-SHA, run) |
| `references/` | `upstream/` checkouts and `papers/` PDFs — git-ignored, re-created by `scripts/` |

External checkouts, videos, datasets, model weights, Docker images and build outputs are never
committed. Their URLs and commit SHAs are recorded in `systems/SYSTEM_INVENTORY.md` and
`literature/SOURCE_LEDGER.md`.
