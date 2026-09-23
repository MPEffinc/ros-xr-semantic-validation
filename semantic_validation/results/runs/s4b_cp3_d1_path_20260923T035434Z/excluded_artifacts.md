# CP3 local-only build/dependency artifacts

No trial raw JSONL, stderr/stdout, input code, generated monitor **source**, or pinned wheel is excluded. The following reproducible trees remain on this workstation but are not staged. Sizes are `du -sh` disk allocations. Digest is SHA-256 of the lexically sorted `sha256sum` listing of every regular file under the named tree, including relative path strings; it is a **tree-manifest digest**, not a single-file SHA-256. Recompute with `find PATH -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum` from repository root.

| Local path relative to this result root | Disk size | Tree-manifest SHA-256 | Exclusion reason |
| --- | ---: | --- | --- |
| `deps/` | 2.7 MiB | `8e33602fc16727c6a042cf28116c1842a3509c593ccbacc095950a41958cc2b4` | pip-installed, platform-specific wheel extraction; pinned wheels included instead. |
| `monitor_ws/build/` | 208 KiB | `41c79021412af9736181ce1fcc4a5b1dfb6e65ba6e8e904b7979d8` | generated colcon build intermediate. |
| `monitor_ws/install/` | 476 KiB | `065d514f2a7b7fe8508a16f68d05c937a0ede52a499d67f9f6f250e47cdc5823` | generated install tree; source/config and build log retained. |
| `monitor_ws/log/` | 64 KiB | `56e3e4ae81ffa430614804b220fe62bc77a12a50f6215c803b3c92f7ccdc344c` | colcon cache/log tree; command stdout/stderr are retained separately. |

| `inputs/__pycache__/` | 36 KiB | `194510a128f08160e28768914107cc36890cbde35e36e3ba1524b6166767847c` | Python bytecode cache; source is included. |

These omissions are for build/cache minimization, not evidence selection. Each trial's raw `environment.stdout` and other raw files are included. No file exceeded GitHub's single-file limit; largest CP3 raw file is `raw/docker_b2_full_setup01/topics.jsonl`, 9,045,651 bytes. No existing source or raw file was deleted.
