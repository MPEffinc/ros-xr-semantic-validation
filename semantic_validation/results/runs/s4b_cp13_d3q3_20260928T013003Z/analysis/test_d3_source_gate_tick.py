"""No-ROS B1 watcher regression on a fixed exact-ID 50 Hz tick fixture."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

inputs = Path(__file__).resolve().parents[1] / 'inputs'


def run():
    with tempfile.TemporaryDirectory(prefix='xrros_d3_gate_') as temp:
        root = Path(temp)
        base = 1_000_000_000
        (root / 'barrier.json').write_text(json.dumps({'start_monotonic_ns': base}))
        with (root / 'sent.jsonl').open('w') as stream:
            for index in range(56):
                sample_ns = base + index * 50_000_000
                payload = {'_qualification': {'sample_id': f'docker:{index}',
                           'generation_id': 1, 'native_state': {'isTracked': True}},
                           'controls': {'teleop_enable': index >= 20}}
                stream.write(json.dumps({'index': index, 'sent': True,
                    'send_ns': sample_ns, 'wire': json.dumps(payload) + '\n'}) + '\n')
            for index in range(56, 76):
                stream.write(json.dumps({'index': index, 'sent': False,
                                         'send_ns': None, 'wire': None}) + '\n')
        with (root / 'd3_ticks.jsonl').open('w') as stream:
            for index in range(300):
                stream.write(json.dumps({'kind': 'health_tick', 'index': index,
                    'tick_id': f'tick:{index}',
                    'tick_monotonic_ns': base + index * 20_000_000}) + '\n')
        (root / 'd3_tick.done').write_text('fixture complete\n')
        env = dict(os.environ, TRIAL_ROOT=str(root), MODE='b1',
                   PYTHONPATH=str(inputs))
        process = subprocess.Popen([sys.executable, str(inputs / 'd3_source_gate_tick.py')],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=env)
        try:
            deadline = time.monotonic() + 5
            while not (root / 'd3_source_gate.done').exists() and time.monotonic() < deadline:
                time.sleep(.01)
            if not (root / 'd3_source_gate.done').exists():
                raise AssertionError('watcher did not process all 300 ticks')
            verdicts = [json.loads(line) for line in (root / 'gate_verdict.jsonl').read_text().splitlines()]
            assert len(verdicts) == 300
            assert all(row['sample_id'] is None for row in verdicts)
            assert verdicts[150]['allowed'] is True
            assert verdicts[151]['allowed'] is False
            assert verdicts[151]['parent_sample_id'] == 'docker:55'
            assert verdicts[151]['trigger_monotonic_ns'] == base + 3_000_000_000
            assert [row['tick_id'] for row in verdicts if row.get('first_detection')] == ['tick:151']
            print('D3_B1_300_TICKS_EXACT_LAST_REAL_SOURCE_TIMEOUT_PASS')
        finally:
            process.terminate()
            process.communicate(timeout=3)


if __name__ == '__main__':
    run()
