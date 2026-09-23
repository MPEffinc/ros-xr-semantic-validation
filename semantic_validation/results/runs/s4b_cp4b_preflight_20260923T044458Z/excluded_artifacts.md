# CP4-B local-only reproducible artifacts

No preflight source, wheel, generated monitor **source**, stdout/stderr or analysis file is excluded. The following copied CP3 install trees remain locally available but are omitted from Git. Sizes are `du -sh` disk allocation. Each digest is SHA-256 of the lexically sorted per-regular-file `sha256sum` listing including paths, not a single archive hash. Recompute from repository root with `find PATH -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum`.

| Path relative to this result root | Disk size | Tree-manifest SHA-256 | Reason |
| --- | ---: | --- | --- |
| `deps/` | 2.7 MiB | `493408dfa2d88f8ed58733037e098b432aa4269ecfc5c17a0ced8c3782e580fc` | Pinned wheels are included; installed Python extraction is rebuildable. |
| `monitor_ws/install/` | 476 KiB | `c924a1a1b183b07b37f6b71d9cb04d32b42fc139702a3cab59ad5d58e167a9b7` | Official generated source and build command are included; colcon install is rebuildable. |

Generated `__pycache__`/`.pyc` and any later colcon build/log trees are local-only non-evidence caches under `.gitignore`. No CP4 runtime raw existed at freeze. Existing CP3 raw/evidence remains untouched.
