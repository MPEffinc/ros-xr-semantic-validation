#!/usr/bin/env python3
"""Host-only execution of prospective D2 sender with an in-process socket pair."""
import contextlib
import importlib.util
import json
import os
import runpy
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'inputs'))
from d1_contract import d1_allow, make_envelope  # noqa: E402


def simulate(mode, regime='full'):
    with tempfile.TemporaryDirectory(prefix='cp7d2_sender_') as temporary:
        folder = Path(temporary)
        start = time.monotonic_ns() + 100_000_000
        (folder / 'barrier.json').write_text(json.dumps({'start_monotonic_ns': start,
                                                         'source_index': 0}))
        a, b = socket.socketpair()
        captured = []

        def drain():
            with b.makefile('r') as stream:
                for line in stream:
                    captured.append(json.loads(line))

        thread = threading.Thread(target=drain)
        thread.start()
        original = socket.create_connection
        old = {k: os.environ.get(k) for k in ('TRIAL_ROOT', 'MODE', 'INFO_REGIME', 'CASE_ID')}
        os.environ.update(TRIAL_ROOT=str(folder), MODE=mode, INFO_REGIME=regime, CASE_ID='D2')
        socket.create_connection = lambda *args, **kwargs: a
        try:
            runpy.run_path(str(ROOT / 'inputs' / 'd1_sender.py'), run_name='__main__')
        finally:
            socket.create_connection = original
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        thread.join(timeout=2)
        assert not thread.is_alive()
        sent = [json.loads(line) for line in (folder / 'sent.jsonl').read_text().splitlines()]
        assert len(sent) == 120 and [r['index'] for r in sent] == list(range(120))
        assert (folder / 'sender.done').exists()
        assert all(r['sample_ns'] >= r['scheduled_ns'] for r in sent)
        assert all(r['sample_ns'] - r['scheduled_ns'] < 5_000_000 for r in sent)
        for row in sent:
            payload = json.loads(row['wire'])
            idx = row['index']
            assert payload['_qualification']['sample_id'] == f'docker:{idx}'
            assert payload['_qualification']['generation_id'] == 1
            assert payload['_qualification']['source_timestamp_ns'] == row['sample_ns']
            assert payload['right_hand']['isTracked'] == (not 56 <= idx < 76)
            assert payload['controls']['teleop_enable'] == (20 <= idx < 76)
            assert payload['right_hand']['pos']['x'] == (.35 if 36 <= idx < 76 else .2)
            assert payload['left_hand']['isTracked'] is True
        expected_wire = 100 if mode == 'b1' else 120
        assert len(captured) == expected_wire
        if mode == 'b1':
            assert [r['index'] for r in sent if not r['allowed']] == list(range(56, 76))
            expected_reason = ('INVALID_TRACKING' if regime == 'full' else
                               'NATIVE_WIRE_ONLY_UNOBSERVABLE_TIME_GENERATION')
            assert all(r['reason'] == expected_reason for r in sent if not r['allowed'])
            assert all(x['right_hand']['isTracked'] for x in captured)
            verdicts = [json.loads(line) for line in (folder / 'gate_verdict.jsonl').read_text().splitlines()]
            assert len(verdicts) == 120
        else:
            assert [x['right_hand']['isTracked'] for x in captured].count(False) == 20
        return dict(mode=mode, regime=regime, planned=120, wire_received=len(captured),
                    max_schedule_lateness_ms=round(max(r['sample_ns'] - r['scheduled_ns']
                                                       for r in sent) / 1e6, 6),
                    false_indices=[r['index'] for r in sent if not r['allowed']])


def property_test():
    spec = importlib.util.spec_from_file_location('d2_property', ROOT / 'inputs' /
                                                   'd1_tloracle_property.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    old = os.environ.get('INFO_REGIME')
    os.environ['INFO_REGIME'] = 'full'
    try:
        values = []
        for tracked, teleop, expected in ((True, True, True),
                                          (False, True, False),
                                          (True, False, True)):
            now = time.monotonic_ns()
            origin = {'origin': 'SOURCE', 'sample_id': 'unit:1',
                      'generation_id': 1, 'source_timestamp_ns': now,
                      'native_state': {'isTracked': tracked}}
            original = {'teleop_enable': teleop, 'tracked': tracked}
            wire = make_envelope(original, origin, now)
            result = module.abstract_message({'data': json.dumps(wire)})['safe']
            assert result is expected
            values.append(result)
        now = time.monotonic_ns()
        neutral = make_envelope({'teleop_enable': False, 'tracked': False},
                                {'origin': 'ORIGINAL_NEUTRAL', 'reason': 'stale_timeout'}, now)
        assert module.abstract_message({'data': json.dumps(neutral)})['safe'] is True
        os.environ['INFO_REGIME'] = 'native'
        assert module.abstract_message({'tracked': True, 'teleop_enable': True})['safe'] is True
        assert module.abstract_message({'tracked': False, 'teleop_enable': True})['safe'] is False
        assert module.abstract_message({'tracked': False, 'teleop_enable': False})['safe'] is True
        return dict(full_valid_active=True, full_invalid_active=False,
                    full_ungripped=True, full_original_timeout_neutral=True,
                    native_valid_active=True, native_invalid_active=False,
                    native_ungripped=True)
    finally:
        if old is None:
            os.environ.pop('INFO_REGIME', None)
        else:
            os.environ['INFO_REGIME'] = old


result = {'sender': [simulate('b0'), simulate('b1', 'full'), simulate('b1', 'native')],
          'property': property_test(), 'status': 'PASS_HOST_ONLY',
          'gazebo_or_defense_qualification': 'NOT_EXECUTED'}
(ROOT / 'preflight' / 'host_preflight.json').write_text(json.dumps(result, indent=2,
                                                               sort_keys=True) + '\n')
print(json.dumps(result, sort_keys=True))
