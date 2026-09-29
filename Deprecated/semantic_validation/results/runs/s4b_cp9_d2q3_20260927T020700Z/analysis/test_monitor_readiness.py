#!/usr/bin/env python3
"""Exercise the exact CP9 DDS-match logging helper without Gazebo."""
import ast
import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'inputs'))
from monitor_readiness import record_monitor_match


class MonitorReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.records = []

    def logger(self, kind, **data):
        # This reproduces trace.log's reserved-key construction, the exact
        # operation that crashed both frozen CP8 B2 cells.
        self.records.append(dict(kind=kind, monotonic_ns=1234, **data))

    def test_cp9_match_reaches_log_and_marker(self):
        match = {'dds_match_monotonic_ns': 1233,
                 'monitor_subscription_count': 1,
                 'output_publishers': ['d1_native_guard'],
                 'official_started_status': True,
                 'receiver_timer_processed_before_match': False}
        record_monitor_match(self.root, match, self.logger)
        self.assertEqual(self.records[0]['kind'], 'pre_spin_monitor_dds_match')
        self.assertEqual(self.records[0]['monotonic_ns'], 1234)
        self.assertEqual(json.loads((self.root / 'monitor_dds_match.ready').read_text()), match)

    def test_frozen_cp8_duplicate_key_is_rejected_before_marker(self):
        with self.assertRaises(ValueError):
            record_monitor_match(self.root, {'monotonic_ns': 1233}, self.logger)
        self.assertFalse((self.root / 'monitor_dds_match.ready').exists())

    def test_actual_d1_nodes_branch_uses_distinct_match_key(self):
        source = Path(__file__).resolve().parents[1] / 'inputs/d1_nodes.py'
        tree = ast.parse(source.read_text())
        matches = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'match'
                                                    for t in node.targets) and isinstance(node.value, ast.Dict):
                matches.append({k.value for k in node.value.keys if isinstance(k, ast.Constant)})
        self.assertEqual(len(matches), 1)
        self.assertIn('dds_match_monotonic_ns', matches[0])
        self.assertNotIn('monotonic_ns', matches[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
