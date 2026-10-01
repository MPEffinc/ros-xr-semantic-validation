"""Pure decision logic of the P1 evidence gates (no ROS). Shared by the ROS gate and host tests.

Each gate sees one evidence observation per poll:
  obs = dict(t, valid, grip, raw=[x,y,z], R=3x3 raw rotation,          # I_ALVR (OpenVR API fields)
             active, epoch)                                            # I_FULL extras (None under I_ALVR)
and decides ARMED / DISARMED.  ARMED -> forward app commands; DISARMED -> drop and stop
(the ROS gate pauses Servo).  All gates arm on the first grip rising edge while valid; they
differ only in what disarms them and in the evidence they are allowed to read.

Defenses (policy fixed in PROTOCOL.md):
  PAUSE      (I_ALVR) disarm on grip falling edge
  REARM_V    (I_ALVR) disarm on grip falling OR valid falling; re-arm needs a fresh rising edge
  REARM_C    (I_FULL) disarm on grip falling OR action-inactive; tracking-only loss does not disarm
  JUMP       (I_ALVR) disarm on grip falling OR raw jump > 5 cm or > 35 deg vs the pose 20 ms earlier
             (Spes thresholds, applied per app sample period of 20 ms)
  EPOCH_G    (I_FULL) disarm on grip falling OR recenter-epoch change
"""
import math

JUMP_LIN = 0.05
JUMP_ANG = math.radians(35)
JUMP_DT = 0.02
I_FULL = {"REARM_C", "EPOCH_G"}


def _angle(Ra, Rb):
    # rotation angle of Ra^T Rb
    tr = sum(Ra[k][i] * Rb[k][i] for i in range(3) for k in range(3))
    return math.acos(max(-1.0, min(1.0, (tr - 1.0) / 2.0)))


class Gate:
    def __init__(self, defense):
        assert defense in {"PAUSE", "REARM_V", "REARM_C", "JUMP", "EPOCH_G"}
        self.d = defense
        self.armed = False
        self.prev = None
        self.hist = []
        self.events = []

    def step(self, obs):
        """Update state from one observation; return (armed, reason_if_changed)."""
        p = self.prev
        self.prev = obs
        self.hist = [o for o in self.hist if obs["t"] - o["t"] <= JUMP_DT + 1e-9] + [obs]
        ref = self.hist[0]
        reason = None
        if p is None:
            return self.armed, None
        rising = obs["grip"] and not p["grip"]
        falling = p["grip"] and not obs["grip"]
        if self.armed:
            if falling:
                reason = "grip_falling"
            elif self.d == "REARM_V" and p["valid"] and not obs["valid"]:
                reason = "valid_falling"
            elif self.d == "REARM_C" and p["active"] and not obs["active"]:
                reason = "action_inactive"
            elif self.d == "JUMP" and obs["valid"] and ref["valid"] and (
                    math.dist(obs["raw"], ref["raw"]) > JUMP_LIN or _angle(ref["R"], obs["R"]) > JUMP_ANG):
                reason = "pose_jump"
            elif self.d == "EPOCH_G" and obs["epoch"] != p["epoch"]:
                reason = "epoch_change"
            if reason:
                self.armed = False
        else:
            ok = obs["valid"] and (obs["active"] if self.d in I_FULL else True)
            if rising and ok:
                self.armed = True
                reason = "grip_rising"
        if reason:
            self.events.append((obs["t"], self.armed, reason))
        return self.armed, reason
