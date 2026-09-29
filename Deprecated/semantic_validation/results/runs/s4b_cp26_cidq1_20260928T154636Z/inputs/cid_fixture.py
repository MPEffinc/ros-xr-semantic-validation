"""XRROS-S4-1.0.0 C-ID Docker fixture: one binding fault injected while moving.

Registered D1 motion shape (20 Hz, 120 slots, 6 s): idle 0-19, reference
20-35, active 36-55 at x=.35 (teleop true), teleop-false tail 56-119. Every
sample is bound at source capture (cid_binding.binding_hash over the INTENDED
ID/generation/stamp/state/command). At slot 50 (moving, armed) one registered
fault kind is injected AFTER binding:
  MISSING_FIELD  generation_id absent from the bound metadata
  MISSING_ID     source-event ID absent
  DUPLICATE_ID   a well-formed, self-consistently bound sample that reuses the
                 already-ingested ID docker:40 (new content time, new ingestion)
  MISMATCH       bound state/command says x=.35, the command payload says x=.65
The old-generation C-ID kind is the D5 formal replay evidence (reused, not a C-ID trial).
"""
SLOTS = 120
PERIOD_NS = 50_000_000
INJECT_INDEX = 50
KINDS = ('MISSING_FIELD', 'MISSING_ID', 'DUPLICATE_ID', 'MISMATCH')
DUPLICATE_OF = 'docker:40'
MISMATCH_X = .65


def spec(index):
    if index < 20:
        return dict(phase='idle', teleop=False, x=.2)
    if index < 36:
        return dict(phase='reference', teleop=True, x=.2)
    if index < 56:
        return dict(phase='active', teleop=True, x=.35)
    return dict(phase='tail', teleop=False, x=.2)
