# Research Questions (refutation-oriented)

- RQ1. In the implemented HORUS stack, which protection goals (PG1–PG6) fail under release, TTL expiry,
  disconnect/reconnect, handoff, and catalog change? (H1–H3)
- RQ2. Do existing primitives, correctly combined (B1), satisfy the goals that stock HORUS fails? (H4)
- RQ3. Is there a residual failure that no standard mechanism closes? (H5; candidate: cross-epoch
  cancel race; known remedy: Chubby-style sequencer)
- RQ4. Is XR essential to any failure, or would any multi-client bridge fail identically? (K3)

A framework is only warranted if RQ3 is answered "yes" with a failure that D-Seq and the other defenses
in `../audit/EXISTING_DEFENSES.md` cannot close.
