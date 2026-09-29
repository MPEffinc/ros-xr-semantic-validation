"""XRROS-S4-1.0.0 D6 Docker fixture: invalidation while moving, then registered recovery.

20 Hz, 200 slots, 10 s post-barrier capture, one connection, generation 1,
fresh per-sample stamps. Registered shape: valid -> invalid for 1 s -> valid
held teleop for .8 s -> release .2 s -> press at current reference -> +.15 X.
  0-19    idle            teleop false, x=.20
  20-35   reference       teleop true,  x=.20
  36-55   active          teleop true,  x=.35   (moving)
  56-75   invalid         teleop true,  x=.35, isTracked FALSE (1 s)
  76-91   valid held      teleop true,  x=.35   (.8 s)
  92-95   release         teleop false, x=.35   (.2 s >= 100 ms)
  96-111  new reference   teleop true,  x=.35   (press at the current reference)
  112-131 subsequent move teleop true,  x=.50   (+.15 X)
  132-199 tail            teleop false, x=.35
"""
SLOTS = 200
PERIOD_NS = 50_000_000
CAPTURE_NS = 10_000_000_000
CLOSE_INDEX = None
RECONNECT_INDEX = None
REPLAY_INDEX = None
INVALID = range(56, 76)
HELD = range(76, 92)
EDGE_INDEX = 96
MOVE = range(112, 132)


def spec(index):
    if index < 20:
        return dict(phase='idle', generation=1, teleop=False, x=.2, tracked=True, sent=True)
    if index < 36:
        return dict(phase='reference', generation=1, teleop=True, x=.2, tracked=True, sent=True)
    if index < 56:
        return dict(phase='active', generation=1, teleop=True, x=.35, tracked=True, sent=True)
    if index < 76:
        return dict(phase='invalid', generation=1, teleop=True, x=.35, tracked=False, sent=True)
    if index < 92:
        return dict(phase='valid_held', generation=1, teleop=True, x=.35, tracked=True, sent=True)
    if index < 96:
        return dict(phase='release', generation=1, teleop=False, x=.35, tracked=True, sent=True)
    if index < 112:
        return dict(phase='new_reference', generation=1, teleop=True, x=.35, tracked=True, sent=True)
    if index < 132:
        return dict(phase='subsequent_active', generation=1, teleop=True, x=.5, tracked=True, sent=True)
    return dict(phase='tail', generation=1, teleop=False, x=.35, tracked=True, sent=True)
