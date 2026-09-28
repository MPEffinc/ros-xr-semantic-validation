"""XRROS-S4-1.0.0 D5 invalidation / recovery state machine (pure logic, no ROS).

One implementation is shared by the B1 source gate, the official B2 TLOracle
property and the B3 mapper check, so each receives the identical policy.

Registered rules (section 5):
* Invalidation: stop accepting motion on the first locally observed invalid
  state, expired age, disconnect, invalid generation or unbound required state;
  the defense latches DISARMED.
* R_EXPLICIT (primary): 500 ms continuously valid/fresh current-generation
  source, THEN teleop release observed for >= 100 ms after that recovery, THEN
  a new rising edge; the edge sample re-arms. Held grip never restarts.
* R_AUTO (secondary): after 500 ms continuously valid/fresh current-generation
  source, re-arm with grip held. Fresh reference capture is provided by the
  original mapper, whose position session resets after >= 250 ms without an
  accepted active message (verified in the pinned hand_pose_mapper.py).
* Ungripped (teleop false) samples pass as intentional neutral; an INVALID one
  still latches DISARMED. A neutral never re-arms by itself.
"""

FRESHNESS_NS = 250_000_000
FUTURE_NS = 5_000_000
DWELL_NS = 500_000_000
RELEASE_NS = 100_000_000


class Rearm:
    def __init__(self, policy, freshness_ns=FRESHNESS_NS):
        if policy not in ('R_EXPLICIT', 'R_AUTO'):
            raise ValueError(policy)
        self.policy = policy
        self.freshness_ns = freshness_ns
        self.armed = True
        self.current_generation = None
        self.valid_since = None
        self.recovered_at = None
        self.release_since = None
        self.released_ok = False
        self.last_fault = None
        self.events = []

    def _fault(self, now_ns, reason):
        first = self.armed
        self.armed = False
        self.valid_since = None
        self.recovered_at = None
        self.release_since = None
        self.released_ok = False
        self.last_fault = reason
        self.events.append(dict(kind='fault', reason=reason, monotonic_ns=now_ns, first_in_episode=first))

    def disconnect(self, now_ns):
        """Explicit locally observed disconnect (source side, or receiver drop)."""
        self._fault(now_ns, 'DISCONNECTED')

    def validity(self, generation, tracked, stamp_ns, now_ns, connection_open):
        if generation is None or stamp_ns is None or tracked is None or connection_open is None:
            return False, 'UNBOUND_REQUIRED_STATE'
        if not connection_open:
            return False, 'DISCONNECTED'
        if self.current_generation is not None and generation < self.current_generation:
            return False, 'OLD_GENERATION'
        if not tracked:
            return False, 'INVALID_TRACKING'
        age = now_ns - stamp_ns
        if age < -FUTURE_NS:
            return False, 'FUTURE_TIME'
        if age > self.freshness_ns:
            return False, 'STALE_SOURCE'
        return True, 'VALID'

    def sample(self, generation, teleop, tracked, stamp_ns, now_ns, connection_open=True):
        """Return (allowed, reason). Must be called with every real source event."""
        valid, reason = self.validity(generation, tracked, stamp_ns, now_ns, connection_open)
        if valid and self.current_generation is not None and generation > self.current_generation:
            self.current_generation = generation
            if self.armed:
                self._fault(now_ns, 'GENERATION_CHANGED')
        elif valid and self.current_generation is None:
            self.current_generation = generation
        if not valid:
            # Any invalid event latches DISARMED and breaks "continuously valid";
            # an ungripped neutral may still pass because it carries no motion.
            self._fault(now_ns, reason)
            return (not teleop), reason
        if self.armed:
            return True, 'ARMED_VALID' if teleop else 'INTENTIONAL_UNGRIPPED_NEUTRAL'
        # DISARMED and this sample is valid.
        if self.valid_since is None:
            self.valid_since = now_ns
        dwell_ok = now_ns - self.valid_since >= DWELL_NS
        if dwell_ok and self.recovered_at is None:
            self.recovered_at = now_ns
            self.events.append(dict(kind='recovered', monotonic_ns=now_ns, valid_since_ns=self.valid_since))
        if self.policy == 'R_AUTO':
            if dwell_ok:
                self._rearm(now_ns, teleop)
                return True, 'R_AUTO_REARMED' if teleop else 'INTENTIONAL_UNGRIPPED_NEUTRAL'
            return (not teleop), 'DISARMED_DWELL' if teleop else 'INTENTIONAL_UNGRIPPED_NEUTRAL'
        # R_EXPLICIT
        if not dwell_ok:
            self.release_since = None
            return (not teleop), 'DISARMED_DWELL' if teleop else 'INTENTIONAL_UNGRIPPED_NEUTRAL'
        if not teleop:
            if self.release_since is None:
                self.release_since = now_ns
            if now_ns - self.release_since >= RELEASE_NS:
                self.released_ok = True
            return True, 'INTENTIONAL_UNGRIPPED_NEUTRAL'
        # teleop true after recovery
        if self.release_since is not None and now_ns - self.release_since >= RELEASE_NS:
            self.released_ok = True
        if self.released_ok:
            self._rearm(now_ns, teleop)
            return True, 'R_EXPLICIT_REARMED_ON_RISING_EDGE'
        self.release_since = None          # held (or re-pressed too early) grip
        return False, 'DISARMED_HELD_GRIP'

    def _rearm(self, now_ns, teleop):
        self.armed = True
        self.events.append(dict(kind='rearm', policy=self.policy, monotonic_ns=now_ns,
                                valid_since_ns=self.valid_since, teleop=teleop))
        self.valid_since = self.recovered_at = self.release_since = None
        self.released_ok = False
