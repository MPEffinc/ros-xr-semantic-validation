"""Non-Gazebo procfs sampler preflight with trial-owned parent/child only."""
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'inputs/resource_sampler.py'
spec = importlib.util.spec_from_file_location('resource_sampler', SOURCE)
sampler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sampler)

with tempfile.TemporaryDirectory(prefix='s4b_q3_proc_') as temp:
    root = Path(temp)
    parent = subprocess.Popen([sys.executable, '-c',
        'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c","import time;time.sleep(5.8)"]);time.sleep(5.8)'],
        start_new_session=True)
    root.joinpath('participant_clock_fake.json').write_text(json.dumps(dict(
        label='fake', pid=parent.pid)))
    root.joinpath('participant_clock_missing.json').write_text(json.dumps(dict(
        label='missing', pid=99999999)))
    deadline = time.monotonic() + 2
    while True:
        before = sampler.snapshot(root, {})
        if any(row['ppid'] == parent.pid for row in before['fake']['processes']):
            break
        assert time.monotonic() < deadline, 'trial-owned child did not start'
        time.sleep(.01)
    assert before['fake']['status'] == 'OBSERVED'
    assert before['missing']['status'] == 'MISSING'
    assert any(row['ppid'] == parent.pid for row in before['fake']['processes'])
    identity = {parent.pid: -1}
    reused = sampler.snapshot(root, identity)
    assert any(row['pid'] == parent.pid and row.get('pid_reuse')
               for row in reused['fake']['processes'])
    env = dict(os.environ, TRIAL_ROOT=str(root))
    proc = subprocess.Popen([sys.executable, str(SOURCE)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(5.25)
    finally:
        proc.terminate()
        out, err = proc.communicate(timeout=5)
        try:
            os.killpg(parent.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        parent.wait(timeout=5)
    assert proc.returncode in (-signal.SIGTERM, 0), (proc.returncode, err)
    data = [json.loads(line) for line in root.joinpath('resource_samples.jsonl').read_text().splitlines()]
    assert data[0]['period_ns'] == 100_000_000
    samples = [row for row in data if row['kind'] == 'sample']
    assert len(samples) >= 50, len(samples)
    intervals = [(b['monotonic_ns'] - a['monotonic_ns']) / 1e6
                 for a, b in zip(samples, samples[1:])]
    assert all(row['targets']['missing']['status'] == 'MISSING' for row in samples)
    assert any(len(row['targets']['fake']['processes']) >= 2 for row in samples)
    assert all('cpu_time_seconds' in proc and 'rss_bytes' in proc and
               'start_ticks' in proc for row in samples
               for proc in row['targets']['fake']['processes'])
    result = dict(status='PASS_NON_GAZEBO_PREFLIGHT', samples=len(samples),
                  interval_min_ms=min(intervals), interval_max_ms=max(intervals),
                  parent_child_observed=True, missing_explicit=True,
                  pid_reuse_detection=True, clock=data[0]['clock'],
                  caveat='No ROS/Gazebo controller or full trial overhead was measured')
    (ROOT / 'analysis/resource_preflight.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))
