# semantic_evidence_framework

**Question.** In XR→ROS teleoperation, how is the evidence that a command is still applicable
acquired and linked, and how is it enforced up to the executing consumer during state transitions?

**Current state: see [`STATUS.md`](STATUS.md).**

| Directory | Contents |
|---|---|
| `docs/` | environment inventory, background and carried-forward conclusions, requirements/threat model, decision log |
| `audit/` | per-implementation code audits: command path, information-delivery tables |
| `literature/` | OpenXR items, comparison systems, rebuttal evidence |
| `hypotheses/` | candidates and go/exclude criteria |
| `experiments/` | protocols and harnesses for minimal reproductions, manual defenses and comparisons |
| `results/` | summaries, trace manifests, hashes (raw data in ignored `results/raw/`) |
| `references/` | upstream pins and versions (checkouts in ignored `references/upstream/`) |

## Rules

- Prior results (S5, authority_continuity, N1, …) are cited as **PRIOR_INTERNAL** and never counted as
  new results.
- `?` means NOT_VERIFIED and is never evidence of a gap.
- Taxonomy, tags, contracts, monitors, state machines and enforcement placement are **not** claimed
  as novel.
