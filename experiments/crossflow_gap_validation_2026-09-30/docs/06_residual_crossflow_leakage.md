# 06 — Residual Cross-flow Leakage after Strong Defenses (Stage 6)

**Status: NOT_RUN experimentally** — no real paired XR+ROS traffic exists (Stage 2). No defended-trace
attacker was trained; no number in this file is an attacker accuracy.

What can be stated without data:

| Defense regime (Stage 5) | Residual cross-flow leakage | Basis |
|---|---|---|
| Regularising constant-rate / constant-size on every flow, session-level padding, rate ≥ peak demand | none beyond session boundaries, for any attacker | construction argument, `05_existing_defenses.md` §2 (D) |
| Same, with adaptive rate switches or demand overflow | leaks via switch/overflow events | known limitation of CS-BuFLO-style adaptivity (via FRONT tables [A]); remedy: fixed rate at peak |
| Zero-delay padding (FRONT, WTF-PAD) per flow | likely remains | DeepCoFFEA S&P'22 [A]: correlation survives WTF-PAD/obfs4 and FRONT — prior art K4 |
| Per-flow DP shaping | bounded by composition of per-flow budgets | inference (D); NetShaper shapes all flows in one tunnel instead [A] |
| Joint shaping (single tunnel / mixing) | removed at the aggregate level | NetShaper [A], Minos [A] |

The outcome pattern that would have kept the item — "XR-only ≈ chance, ROS-only ≈ chance, paired XR+ROS ≫
chance, re-paired ≈ chance" — **cannot occur** under the first regime, and under the weaker regimes it would
reproduce known results (K4) whose remedy (a regularising or joint shaper) already exists.
