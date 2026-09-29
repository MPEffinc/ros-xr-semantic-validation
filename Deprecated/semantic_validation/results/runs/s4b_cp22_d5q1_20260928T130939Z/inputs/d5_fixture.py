"""XRROS-S4-1.0.0 D5 Docker fixture: moving disconnect, new generation, old-generation replay.

20 Hz, 200 slots, 10 s post-barrier capture. Every real sample has its own fresh
stamp (its creation time). Registered shape:
  0-19    idle            gen 1, teleop false, x=.20
  20-35   reference       gen 1, teleop true,  x=.20
  36-55   active          gen 1, teleop true,  x=.35  (moving)
  56-69   disconnected    connection closed by the source at slot 56 (t=2.8 s); no bytes
  70-89   new generation  gen 2, teleop HELD,  x=.50  (new connection at slot 70, t=3.5 s,
                          i.e. .7 s after close; new reference pose)
    72    old-gen replay  gen 1, teleop true,  x=.35  (presented after reconnect)
  90-93   release         gen 2, teleop false, x=.50  (0.2 s >= 100 ms)
  94-109  new reference   gen 2, teleop true,  x=.50  (rising edge at 94)
  110-129 subsequent move gen 2, teleop true,  x=.65  (+.15 X)
  130-199 tail            gen 2, teleop false, x=.50
"""
SLOTS = 200
PERIOD_NS = 50_000_000
CLOSE_INDEX = 56
RECONNECT_INDEX = 70
REPLAY_INDEX = 72
CAPTURE_NS = 10_000_000_000


def spec(index):
    if index < 20:
        return dict(phase='idle', generation=1, teleop=False, x=.2, sent=True)
    if index < 36:
        return dict(phase='reference', generation=1, teleop=True, x=.2, sent=True)
    if index < 56:
        return dict(phase='active', generation=1, teleop=True, x=.35, sent=True)
    if index < 70:
        return dict(phase='disconnected', generation=None, teleop=None, x=None, sent=False)
    if index == REPLAY_INDEX:
        return dict(phase='old_generation_replay', generation=1, teleop=True, x=.35, sent=True)
    if index < 90:
        return dict(phase='new_generation_held', generation=2, teleop=True, x=.5, sent=True)
    if index < 94:
        return dict(phase='release', generation=2, teleop=False, x=.5, sent=True)
    if index < 110:
        return dict(phase='new_reference', generation=2, teleop=True, x=.5, sent=True)
    if index < 130:
        return dict(phase='subsequent_active', generation=2, teleop=True, x=.65, sent=True)
    return dict(phase='tail', generation=2, teleop=False, x=.5, sent=True)
