#!/usr/bin/env python3
"""No-Gazebo scorer regressions: (1) apply the scorer to the retained C-MON Q3
setup raw (setup evidence, not formal outcomes) as a fixture; (2) synthetic
checks of the request-delay boundary band and the premature-stop rule."""
import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cmon_formal_audit as audit  # noqa: E402

Q3RAW = audit.Q / 'raw'


def q3_row(cell):
    return dict(order='1', case='CMON', repetition='1', fault=cell['fault'], mode=cell['mode'], baseline=cell['baseline'],
                regime=cell['regime'], composed=cell['composed'], expect_motion=cell['expect_motion'],
                trial_id=cell['trial_id'], seed='20260922')


class Q3Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = audit.RAW
        audit.RAW = Q3RAW
        with (audit.Q / 'qualification_schedule.csv').open() as f:
            cls.cells = {r['trial_id']: q3_row(r) for r in csv.DictReader(f)}
        cls.out = {k: audit.score_row(v) for k, v in cls.cells.items()}

    @classmethod
    def tearDownClass(cls):
        audit.RAW = cls.saved

    def get(self, arm, regime, fault):
        return self.out[f'docker_{arm}_{regime}_{fault}_cmonq3s01']

    def test_all_valid(self):
        self.assertEqual({t['comparison_status'] for t in self.out.values()}, {'VALID_FORMAL_TRIAL'})

    def test_composed_and_gates_pass_with_attribution(self):
        for arm, regime, fault, attr in (
                ('b2c', 'full', 'ORACLE_ABSENT', 'B2_COMPOSED'), ('b2c', 'full', 'ORACLE_DISCONNECT', 'B2_COMPOSED'),
                ('b2c', 'full', 'ORACLE_NONRESPONSIVE', 'B2_COMPOSED'), ('b2c', 'native', 'ORACLE_DISCONNECT', 'B2_COMPOSED'),
                ('b1', 'full', 'B1_GATE_FAIL', 'HEARTBEAT'), ('b3', 'full', 'B3_GATE_FAIL', 'HEARTBEAT')):
            t = self.get(arm, regime, fault)
            self.assertEqual(t['policy_status'], 'PASS_POLICY', (arm, fault, t.get('policy_violations')))
            self.assertIn(attr, t['detection_and_stop_attribution'])

    def test_native_is_measured_fail_open(self):
        for regime, fault in (('full', 'ORACLE_ABSENT'), ('full', 'ORACLE_DISCONNECT'),
                              ('full', 'ORACLE_NONRESPONSIVE'), ('native', 'ORACLE_DISCONNECT')):
            t = self.get('b2', regime, fault)
            self.assertEqual(t['policy_status'], 'FAIL_POLICY')
            self.assertIn('M2_NO_EXPLICIT_NEUTRALIZATION_REQUEST', t['policy_violations'])
            self.assertGreater(t['official_path']['forwarded_to_original_consumer_after_trigger'], 0)


class Synthetic(unittest.TestCase):
    def score(self, request_offset_ms, fault='ORACLE_DISCONNECT'):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        src = Q3RAW / 'docker_b2c_full_ORACLE_DISCONNECT_cmonq3s01'
        dst = tmp / 'docker_b2c_full_ORACLE_DISCONNECT_cmonq3s01'
        shutil.copytree(src, dst)
        t_fault = next(r for r in audit.rows(dst / 'cmon_fault.jsonl') if r['kind'] == 'injected')['injected_monotonic_ns']
        sa = audit.rows(dst / 'stop_adapter.jsonl')
        for r in sa:
            if r['kind'] == 'stop_request':
                r['monotonic_ns'] = t_fault + int(request_offset_ms * 1e6)
        (dst / 'stop_adapter.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in sa))
        saved = audit.RAW
        audit.RAW = tmp
        try:
            return audit.score_row(dict(order='1', case='CMON', repetition='1', fault=fault, mode='b2', baseline='b2c',
                                        regime='full', composed='1', expect_motion='1',
                                        trial_id='docker_b2c_full_ORACLE_DISCONNECT_cmonq3s01', seed='20260922'))
        finally:
            audit.RAW = saved

    def test_band(self):
        self.assertEqual(self.score(49.5)['policy_status'], 'UNKNOWN_BOUNDARY_STRADDLE')
        self.assertIn('M2_NEUTRALIZATION_REQUEST_OVER_ALLOWANCE_PLUS_50MS', self.score(51.5)['policy_violations'])
        self.assertEqual(self.score(48.0)['policy_status'], 'PASS_POLICY')

    def test_premature(self):
        self.assertIn('M1_NEUTRALIZATION_BEFORE_LOCAL_TRIGGER', self.score(-2.0)['policy_violations'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
