#!/usr/bin/env python3
"""Host-only A-H regression of nondefensive cached-source attribution."""
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'inputs'))
from mapper_lineage_state import MapperLineageState


def edge(i, generation=1, payload='same'):
    return {'command_id': f'receiver:{i}', 'parent': {
        'sample_id': f'docker:{i}', 'generation_id': generation},
        'payload_sha256': payload}


class MapperLineageTests(unittest.TestCase):
    def setUp(self):
        self.state = MapperLineageState()

    def accept(self, candidate):
        self.state.observe(candidate)
        self.state.apply_after_original_callback(candidate,
                                                 {'tracked': True, 'have_target': True})

    def test_a_accepted_then_rejected(self):
        accepted, rejected = edge(55), edge(56)
        self.accept(accepted)
        self.state.observe(rejected)
        self.state.reject(rejected)
        self.assertIs(self.state.timer_parent(), accepted)
        self.assertIs(self.state.snapshot()['last_rejected'], rejected)

    def test_b_multiple_rejected(self):
        accepted = edge(55)
        self.accept(accepted)
        for i in range(56, 76):
            rejected = edge(i)
            self.state.observe(rejected)
            self.state.reject(rejected)
            self.assertIs(self.state.timer_parent(), accepted)

    def test_c_repeated_timer_publications(self):
        accepted = edge(55)
        self.accept(accepted)
        self.state.observe(edge(56))
        self.state.reject(self.state.last_observed)
        self.assertTrue(all(self.state.timer_parent() is accepted for _ in range(100)))

    def test_d_reject_concurrent_with_timer_read(self):
        accepted = edge(55)
        self.accept(accepted)
        parents = []
        def timer():
            for _ in range(2000):
                parents.append(self.state.timer_parent())
        worker = threading.Thread(target=timer)
        worker.start()
        for i in range(56, 76):
            rejected = edge(i)
            self.state.observe(rejected)
            self.state.reject(rejected)
        worker.join()
        self.assertTrue(parents)
        self.assertTrue(all(parent is accepted for parent in parents))

    def test_e_new_accepted_after_rejection(self):
        self.accept(edge(55))
        self.state.observe(edge(56))
        self.state.reject(self.state.last_observed)
        accepted = edge(76)
        self.accept(accepted)
        self.assertIs(self.state.timer_parent(), accepted)

    def test_f_generation_transition(self):
        self.accept(edge(55, generation=1))
        next_generation = edge(0, generation=2)
        self.accept(next_generation)
        self.assertEqual(self.state.timer_parent()['parent']['generation_id'], 2)

    def test_g_duplicate_canonical_payloads_not_identity(self):
        first, second = edge(55, payload='identical'), edge(56, payload='identical')
        self.accept(first)
        self.assertIs(self.state.timer_parent(), first)
        # Ambiguous payload registry must supply None, never guess a parent.
        self.state.observe(None)
        self.state.reject(None)
        self.assertIs(self.state.timer_parent(), first)
        self.accept(second)
        self.assertIs(self.state.timer_parent(), second)

    def test_h_no_valid_parent(self):
        self.assertIsNone(self.state.timer_parent())
        self.state.observe(None)
        self.state.apply_after_original_callback(None,
                                                 {'tracked': False, 'have_target': False})
        self.assertIsNone(self.state.timer_parent())


if __name__ == '__main__':
    unittest.main(verbosity=2)
