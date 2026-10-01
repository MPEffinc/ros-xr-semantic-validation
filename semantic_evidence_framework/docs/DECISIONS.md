# Decision log

| ID | Date | Decision | Reason |
|---|---|---|---|
| D-001 | 2026-10-01 | Work in a separate worktree `/home/cclab/ros_xr_evidence` on `research/xr-ros-evidence-framework` | The primary checkout is on the N1 branch and holds that branch's ignored data |
| D-002 | 2026-10-01 | Archive `authority_continuity/` and `xr_demo_integrity/` under `archive/2026-10-01_closed_research/`; keep `Deprecated/` in place | Both are closed; `Deprecated/` is already an archive |
| D-003 | 2026-10-01 | Do not import `experiments/` (cross-flow, N1) from the N1 branch; reference it by commit | Brief: do not merge closed research in order to read it |
| D-004 | 2026-10-01 | Reuse the S-track upstream checkouts read-only from the primary checkout instead of re-cloning | Same pinned SHAs; avoids divergent copies. New upstreams go to `references/upstream/` (ignored) |
| D-005 | 2026-10-01 | Leave the three long-running containers of other work untouched | Not ours; recorded as concurrent load |
