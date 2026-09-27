#!/usr/bin/env python3
"""Host-only positive/negative fixtures for prospectively frozen CP8 checks."""
import json
import tempfile
import unittest
from pathlib import Path

from cp8_qualification_audit import mapper_cache_audit, monitor_call_audit


def write_rows(root, name, records):
    (root / name).write_text(''.join(json.dumps(r) + '\n' for r in records))


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_monitor_positive_exact_call_return_and_ack(self):
        write_rows(self.root, 'lineage.jsonl', [
            {'kind': 'pre_spin_monitor_dds_match', 'monotonic_ns': 1},
            {'kind': 'publish', 'stage': 'receiver_envelope', 'monitor_event_id': 7,
             'monotonic_ns': 2},
            {'kind': 'monitor_input_publish_call_return', 'monitor_event_id': 7,
             'dds_subscription_count_after': 1, 'monotonic_ns': 3}])
        (self.root / 'monitor_dds_match.ready').write_text('{}')
        self.assertEqual(monitor_call_audit(self.root)['status'], 'PASS')

    def test_monitor_negative_early_publish(self):
        write_rows(self.root, 'lineage.jsonl', [
            {'kind': 'publish', 'stage': 'receiver_envelope', 'monitor_event_id': 7,
             'monotonic_ns': 1},
            {'kind': 'pre_spin_monitor_dds_match', 'monotonic_ns': 2},
            {'kind': 'monitor_input_publish_call_return', 'monitor_event_id': 7,
             'dds_subscription_count_after': 1, 'monotonic_ns': 3}])
        (self.root / 'monitor_dds_match.ready').write_text('{}')
        self.assertIn('RECEIVER_PUBLISHED_BEFORE_DDS_MATCH',
                      monitor_call_audit(self.root)['issues'])

    def test_mapper_positive_cached_parent_after_rejection(self):
        parent = {'command_id': 'receiver:55', 'parent': {'sample_id': 'docker:55'}}
        records = ([{'kind': 'mapper_applied_after_original_callback', 'exact_parent': parent}] +
                   [{'kind': 'b3_mapper_verdict', 'verdict': False,
                     'source_origin': {'sample_id': f'docker:{i}'}} for i in range(56, 76)])
        records.append({'kind': 'publish', 'stage': 'mapper', 'command_id': 'mapper:466',
                        'parent': parent, 'payload': {'twist': {'linear': {'x': .09}}}})
        write_rows(self.root, 'lineage.jsonl', records)
        result = mapper_cache_audit(self.root, 'b3')
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['cached_nonzero_after_reject'][0]['last_applied_source'],
                         'docker:55')

    def test_mapper_negative_rejected_parent(self):
        accepted = {'command_id': 'receiver:55', 'parent': {'sample_id': 'docker:55'}}
        rejected = {'command_id': 'receiver:56', 'parent': {'sample_id': 'docker:56'}}
        records = ([{'kind': 'mapper_applied_after_original_callback', 'exact_parent': accepted}] +
                   [{'kind': 'b3_mapper_verdict', 'verdict': False,
                     'source_origin': {'sample_id': f'docker:{i}'}} for i in range(56, 76)])
        records.append({'kind': 'publish', 'stage': 'mapper', 'command_id': 'mapper:466',
                        'parent': rejected, 'payload': {'twist': {'linear': {'x': .09}}}})
        write_rows(self.root, 'lineage.jsonl', records)
        self.assertEqual(mapper_cache_audit(self.root, 'b3')['status'],
                         'BLOCKED_MEASUREMENT')


if __name__ == '__main__':
    unittest.main(verbosity=2)
