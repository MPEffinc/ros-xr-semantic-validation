# LTS0429 run sequence (transparency note)

Three runs of `harness/lts0429_udp_runtime.py` exist for 2026-09-14. All three
used the same unmodified upstream binary and the same synthetic UDP inputs; only
the harness's *expected* values changed, and only for the malformed-token trial.

| Run | Result | What changed |
| --- | --- | --- |
| `lts0429_udp_runtime_20260914T065231Z` | 6/7 | Initial expectation was that `LeftHandPos:0.1,NaNvalue,0.3` would throw out of `std::stod` and stop the receive thread. Observed instead: `std::stod` accepts the `NaN` prefix, so a **non-finite pose was published**. |
| `lts0429_udp_runtime_20260914T065330Z` | 7/8 | Trial split into `t7a` (NaN token, accepted and published — confirmed) and `t7b` (non-numeric token `abc`). `t7b` expected the process to survive with a dead receive thread. Observed instead: the uncaught `std::invalid_argument` on the receive thread calls `std::terminate` and **aborts the whole process**. |
| `lts0429_udp_runtime_20260914T065407Z` | **8/8, canonical** | `t7b` expectation corrected to the observed process abort; node stdout captured as `terminate called after throwing an instance of 'std::invalid_argument' / what(): stod`. |

No upstream source was modified at any point. The earlier two runs are retained
because the corrected expectations were *derived from* their observed output.
