"""No-Gazebo 300-tick runtime check for the separate common health clock."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

root = Path(os.environ['TRIAL_ROOT'])
root.mkdir(parents=True, exist_ok=True)
os.environ['MODE'] = 'b0'
child = subprocess.Popen([sys.executable, '/code/d3_tick_publisher.py'],
                         stdout=(root / 'tick.stdout').open('w'),
                         stderr=(root / 'tick.stderr').open('w'),
                         start_new_session=True, env=os.environ.copy())
result = {}
try:
    deadline = time.monotonic() + 5
    while not (root / 'd3_tick.ready').exists() and time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError(f'tick child exited {child.returncode} before ready')
        time.sleep(.005)
    if not (root / 'd3_tick.ready').exists():
        raise RuntimeError('tick ready marker absent')
    start_ns = time.monotonic_ns() + 100_000_000
    (root / 'barrier.json').write_text(json.dumps({'start_monotonic_ns': start_ns}))
    deadline = time.monotonic() + 8
    while not (root / 'd3_tick.done').exists() and time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError(f'tick child exited {child.returncode} during schedule')
        time.sleep(.005)
    if not (root / 'd3_tick.done').exists():
        raise RuntimeError('300-tick completion marker absent')
    ticks = [json.loads(line) for line in (root / 'd3_ticks.jsonl').read_text().splitlines()]
    assert len(ticks) == 300
    assert [row['index'] for row in ticks] == list(range(300))
    assert all(row['source_sample_id'] is None and row['source_receipt_ns'] is None
               for row in ticks)
    actual = [row['tick_monotonic_ns'] for row in ticks]
    lateness = [row['tick_monotonic_ns'] - (start_ns + row['index'] * 20_000_000)
                for row in ticks]
    assert all(b > a for a, b in zip(actual, actual[1:]))
    result = {'status': 'PASS_COMPONENT_PREFLIGHT', 'tick_count': len(ticks),
              'source_samples_created': 0,
              'max_schedule_lateness_ms': max(lateness) / 1e6,
              'min_schedule_lateness_ms': min(lateness) / 1e6,
              'max_interval_ms': max(b-a for a,b in zip(actual,actual[1:])) / 1e6,
              'mean_interval_ms': (actual[-1]-actual[0]) / 299 / 1e6}
    if max(lateness) >= 20_000_000:
        result['status'] = 'FAIL_COMPONENT_PREFLIGHT_MISSED_50HZ_CYCLE'
except Exception as error:
    result = {'status': 'FAIL_COMPONENT_PREFLIGHT', 'error': repr(error)}
finally:
    if child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)
    child.wait(timeout=3)
    (root / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps(result, sort_keys=True))
if result['status'] != 'PASS_COMPONENT_PREFLIGHT':
    raise SystemExit(1)
