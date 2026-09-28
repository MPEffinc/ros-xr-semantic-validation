#!/usr/bin/env python3
"""No-Gazebo D5 state-machine regressions (registered R_EXPLICIT / R_AUTO rules)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'inputs'))
from d5_rearm import Rearm  # noqa: E402
import d5_fixture as fx  # noqa: E402

MS = 1_000_000


def feed(r, t_ms, gen=2, teleop=True, tracked=True, age_ms=1, open_=True):
    now = t_ms * MS
    return r.sample(gen, teleop, tracked, now - age_ms * MS, now, open_)


class Unit(unittest.TestCase):
    def fresh(self, policy):
        r = Rearm(policy)
        self.assertEqual(feed(r, 0, gen=1), (True, 'ARMED_VALID'))
        return r

    def test_disconnect_while_moving_then_new_generation(self):
        for policy in ('R_EXPLICIT', 'R_AUTO'):
            r = self.fresh(policy)
            r.disconnect(100 * MS)
            self.assertFalse(r.armed)
            self.assertEqual(feed(r, 800), (False, 'DISARMED_DWELL'))          # new gen, held, no dwell yet
            self.assertEqual(r.current_generation, 2)

    def test_old_generation_after_reconnect_rejected_and_resets_dwell(self):
        r = self.fresh('R_AUTO')
        r.disconnect(100 * MS)
        feed(r, 800)
        self.assertEqual(feed(r, 900, gen=1), (False, 'OLD_GENERATION'))
        self.assertIsNone(r.valid_since)
        self.assertEqual(feed(r, 950)[0], False)
        self.assertEqual(feed(r, 1400)[0], False)                              # 450 ms after replay
        self.assertEqual(feed(r, 1450), (True, 'R_AUTO_REARMED'))              # 500 ms continuously valid

    def test_r_explicit_held_grip_never_restarts(self):
        r = self.fresh('R_EXPLICIT')
        r.disconnect(100 * MS)
        for t in range(800, 3000, 50):
            self.assertEqual(feed(r, t), (False, 'DISARMED_HELD_GRIP' if t >= 1300 else 'DISARMED_DWELL'))
        self.assertFalse(r.armed)

    def test_r_explicit_release_too_short(self):
        r = self.fresh('R_EXPLICIT')
        r.disconnect(100 * MS)
        for t in range(800, 1350, 50):
            feed(r, t)
        feed(r, 1350, teleop=False)
        feed(r, 1400, teleop=False)                      # 50 ms release
        self.assertEqual(feed(r, 1449), (False, 'DISARMED_HELD_GRIP'))

    def test_r_explicit_release_before_dwell_does_not_count(self):
        r = self.fresh('R_EXPLICIT')
        r.disconnect(100 * MS)
        feed(r, 800, teleop=False)
        feed(r, 1000, teleop=False)                      # release inside the dwell
        self.assertEqual(feed(r, 1300 + 1)[0], False)    # dwell just complete, no release after it

    def test_r_explicit_correct_release_and_edge(self):
        r = self.fresh('R_EXPLICIT')
        r.disconnect(100 * MS)
        for t in range(800, 1350, 50):
            feed(r, t)
        feed(r, 1350, teleop=False)
        feed(r, 1450, teleop=False)
        self.assertEqual(feed(r, 1460), (True, 'R_EXPLICIT_REARMED_ON_RISING_EDGE'))
        self.assertTrue(r.armed)
        self.assertEqual(feed(r, 1510), (True, 'ARMED_VALID'))

    def test_valid_dwell_shorter_than_500ms(self):
        r = self.fresh('R_AUTO')
        r.disconnect(100 * MS)
        feed(r, 800)
        self.assertEqual(feed(r, 1299), (False, 'DISARMED_DWELL'))
        self.assertEqual(feed(r, 1300), (True, 'R_AUTO_REARMED'))

    def test_invalid_states_fault(self):
        for kwargs, reason in ((dict(tracked=False), 'INVALID_TRACKING'), (dict(age_ms=300), 'STALE_SOURCE'),
                               (dict(age_ms=-6), 'FUTURE_TIME'), (dict(open_=False), 'DISCONNECTED')):
            r = self.fresh('R_AUTO')
            self.assertEqual(feed(r, 100, gen=1, **kwargs), (False, reason))
            self.assertFalse(r.armed)

    def test_missing_or_mismatched_binding(self):
        r = self.fresh('R_EXPLICIT')
        self.assertEqual(r.sample(None, True, True, 0, 100 * MS, True), (False, 'UNBOUND_REQUIRED_STATE'))
        r = self.fresh('R_EXPLICIT')
        self.assertEqual(r.sample(1, True, True, None, 100 * MS, True), (False, 'UNBOUND_REQUIRED_STATE'))
        r = self.fresh('R_EXPLICIT')
        self.assertEqual(r.sample(1, True, True, 100 * MS, 100 * MS, None), (False, 'UNBOUND_REQUIRED_STATE'))

    def test_ungripped_neutral_passes_but_invalid_one_latches(self):
        r = self.fresh('R_AUTO')
        self.assertEqual(feed(r, 50, gen=1, teleop=False), (True, 'INTENTIONAL_UNGRIPPED_NEUTRAL'))
        self.assertEqual(feed(r, 100, gen=1, teleop=False, tracked=False), (True, 'INVALID_TRACKING'))
        self.assertFalse(r.armed)

    def test_generation_increase_without_disconnect_disarms(self):
        r = self.fresh('R_AUTO')
        self.assertEqual(feed(r, 100, gen=2)[0], False)
        self.assertEqual(r.last_fault, 'GENERATION_CHANGED')


class FixtureTimeline(unittest.TestCase):
    """Whole D5 fixture at a location with 0.2 ms transport; tick-free source view."""
    def run_fixture(self, policy):
        r = Rearm(policy)
        out = {}
        for i in range(fx.SLOTS):
            s = fx.spec(i)
            t = i * fx.PERIOD_NS + 200_000
            if i == fx.CLOSE_INDEX:
                r.disconnect(t)
            if not s['sent']:
                continue
            out[i] = r.sample(s['generation'], s['teleop'], True, i * fx.PERIOD_NS, t, True)
        return r, out

    def test_r_explicit_timeline(self):
        r, out = self.run_fixture('R_EXPLICIT')
        self.assertTrue(all(out[i][0] for i in range(0, 56)))
        self.assertEqual(out[fx.REPLAY_INDEX], (False, 'OLD_GENERATION'))
        self.assertFalse(any(out[i][0] for i in range(70, 90)))            # held grip never restarts
        self.assertTrue(all(out[i][0] for i in range(90, 94)))             # release passes as neutral
        self.assertEqual(out[94], (True, 'R_EXPLICIT_REARMED_ON_RISING_EDGE'))
        self.assertTrue(all(out[i][0] for i in range(94, 200)))
        rearm = [e for e in r.events if e['kind'] == 'rearm']
        self.assertEqual(len(rearm), 1)

    def test_r_auto_timeline(self):
        r, out = self.run_fixture('R_AUTO')
        self.assertEqual(out[fx.REPLAY_INDEX], (False, 'OLD_GENERATION'))
        first = min(i for i in range(70, 90) if out[i][0])
        self.assertEqual(first, 83)                                          # replay at 72 restarts the dwell
        self.assertEqual(out[first], (True, 'R_AUTO_REARMED'))
        rearm = [e for e in r.events if e['kind'] == 'rearm']
        self.assertGreaterEqual(rearm[0]['monotonic_ns'] - rearm[0]['valid_since_ns'], 500 * MS)
        self.assertTrue(all(out[i][0] for i in range(first, 200)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
