#!/usr/bin/env python3
"""No-Gazebo regression for exact local trigger and frozen scorer contracts."""
import json
import tempfile
import unittest
from pathlib import Path

import formal_audit as formal
from local_trigger import local_invalid_observation


class FormalAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_exact_source_id_not_nearest_time(self):
        records = [
            {'kind':'source_received','monotonic_ns':1001,
             'metadata':{'sample_id':'docker:55'}},
            {'kind':'source_received','monotonic_ns':1200,
             'metadata':{'sample_id':'docker:56'}},
            {'kind':'source_received','monotonic_ns':1199,
             'metadata':{'sample_id':'docker:57'}}]
        (self.root/'lineage.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in records))
        self.assertEqual(local_invalid_observation(self.root,'b2',1000,formal.rows),1200)
        self.assertEqual(local_invalid_observation(self.root,'b1',1000,formal.rows),1000)

    def test_missing_exact_source_is_unknown(self):
        (self.root/'lineage.jsonl').write_text(json.dumps({
            'kind':'source_received','monotonic_ns':1001,
            'metadata':{'sample_id':'docker:55'}})+'\n')
        self.assertIsNone(local_invalid_observation(self.root,'b3',1000,formal.rows))

    def test_observational_shim_not_defense(self):
        self.assertEqual(formal.percentile([1,2,3,4,5],.95),5)
        self.assertEqual(formal.ELIGIBLE, {f'docker:{i}' for i in range(36,56)})
        self.assertEqual(formal.FORBIDDEN, {f'docker:{i}' for i in range(56,76)})


if __name__ == '__main__':
    unittest.main(verbosity=2)
