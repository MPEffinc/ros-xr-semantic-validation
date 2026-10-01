# Status

| Phase | Status | Commit | Remote verified | Notes |
|---|---|---|---|---|
| 0 Inspection + backup tag | DONE | tag `archive/pre-authority-continuity-20260929` → `e7799a7` (tag obj `6c27e2e`) | yes (`git ls-remote`) | local == origin/main, clean, no LFS, no submodules, main unprotected, repo public |
| 1 Archive into `Deprecated/` | DONE | `5141e70bc3cf0d49b261103b097b77c9f07587c2` | yes | blob listing identical; see `Deprecated/ARCHIVE_MANIFEST.md` |
| 2 Workspace init | DONE | `127265fb88bafbe077f620467f8792713b7941b1` | yes | |
| 3 Literature | DONE | `d4cc51f47224290a9198e84de6a81db7020f5ec9` | yes | 9 key sources + supporting; no cross-line citation edges; no author-stated limitation on lease→execution consistency |
| 4 HORUS code audit | DONE | `255715ac83cf829754775fa5febb245fe866d5e0` | yes | F1–F9 SOURCE_CONFIRMED / NOT_VERIFIED; Unity client closed-source |
| 5 Threat model / defenses | DONE | `2d0e42451000156659d810133beafa713ae16910` | yes | Q-SEC = no gap (no auth, acknowledged); Q-CONS testable; GO for minimal experiments only, NO-GO for framework |
| 6 Minimal experiments | DONE | freeze `421a0507306a2136e566d9cd3b816976feca3c02`; results `f8100f450830b68ad8534a4e6bcc2d977c6b0937` | yes | 120 formal trials, 0 errors; B0 fails PG2/PG3-stop/PG4/PG5, B1 passes all; H5 race not observed 0/25 |
| 7 Verdict | DONE | (this commit) | — | **IMPLEMENTATION_GAP_ONLY**; no framework developed |

Upstream pins observed 2026-09-29 (`git ls-remote HEAD`):
`RICE-unige/horus_ros2` `eca75cbf559f09ff793d8993338b2f1ffed1adfd`,
`RICE-unige/horus` `819cdfdc74f1a0c2bd73946dc14897a533f68b61`,
`RICE-unige/horus_sdk` `f4f00dab41910676519d545515531ec243414044`,
`moveit/moveit2` `a2117df217dc3620b6f1a5d2d150a20e40aa7c7c`.
These equal the HORUS revisions used by the archived August-2026 track.
