# Status

| Phase | Status | Commit | Remote verified | Notes |
|---|---|---|---|---|
| 0 Inspection + backup tag | DONE | tag `archive/pre-authority-continuity-20260929` → `e7799a7` (tag obj `6c27e2e`) | yes (`git ls-remote`) | local == origin/main, clean, no LFS, no submodules, main unprotected, repo public |
| 1 Archive into `Deprecated/` | DONE | `5141e70bc3cf0d49b261103b097b77c9f07587c2` | yes | blob listing identical; see `Deprecated/ARCHIVE_MANIFEST.md` |
| 2 Workspace init | DONE | (this commit; SHA recorded in next update) | — | |
| 3 Literature | NOT_STARTED | | | |
| 4 HORUS code audit | NOT_STARTED | | | |
| 5 Threat model / defenses | NOT_STARTED | | | |
| 6 Minimal experiments | NOT_RUN | | | gated on 5 |
| 7 Verdict | NOT_STARTED | | | |

Upstream pins observed 2026-09-29 (`git ls-remote HEAD`):
`RICE-unige/horus_ros2` `eca75cbf559f09ff793d8993338b2f1ffed1adfd`,
`RICE-unige/horus` `819cdfdc74f1a0c2bd73946dc14897a533f68b61`,
`RICE-unige/horus_sdk` `f4f00dab41910676519d545515531ec243414044`,
`moveit/moveit2` `a2117df217dc3620b6f1a5d2d150a20e40aa7c7c`.
These equal the HORUS revisions used by the archived August-2026 track.
