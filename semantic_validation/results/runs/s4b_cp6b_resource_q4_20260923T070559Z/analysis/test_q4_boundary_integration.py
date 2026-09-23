"""Host-only integration of Q4 wrapper, regular sampler, boundary, analyzer."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'inputs'))
from resource_sampler import snapshot, HZ, PERIOD_NS, PAGE_SIZE
from lifecycle_resource_audit import trial


def exercise(with_boundary=True):
    with tempfile.TemporaryDirectory(prefix='xr_q4_boundary_') as tmp:
        path = Path(tmp)
        marker = path / 'capture_end.ready'
        env = dict(os.environ, XR_CAPTURE_END_MARKER=str(marker),
                   XR_SENDER_ACCOUNTING=str(path / 'sender_lifecycle.json'))
        argv = [sys.executable, str(ROOT / 'inputs/sender_lifecycle_wrapper.py'),
                sys.executable, '-c',
                'import time; t=time.monotonic()+.34; exec("while time.monotonic()<t: pass")']
        child = subprocess.Popen(argv, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        (path / 'participant_clock_sender.json').write_text(json.dumps(dict(label='sender', pid=child.pid)))
        metadata = dict(kind='resource_metadata', clock='CLOCK_MONOTONIC',
                        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                        time_namespace=os.readlink('/proc/self/ns/time'),
                        ticks_per_second=HZ, page_size=PAGE_SIZE, period_ns=PERIOD_NS)
        start = time.monotonic_ns()
        samples = []
        identities = {}
        for index in range(6):
            deadline = start + index * PERIOD_NS
            if time.monotonic_ns() < deadline:
                time.sleep((deadline - time.monotonic_ns()) / 1e9)
            samples.append(dict(kind='sample', index=index,
                                monotonic_ns=time.monotonic_ns(),
                                targets=snapshot(path, identities)))
        before = time.monotonic_ns()
        targets = snapshot(path, identities)
        after = time.monotonic_ns()
        if with_boundary:
            (path / 'resource_capture_boundary.json').write_text(json.dumps(dict(
                acquisition_start_ns=before, acquisition_end_ns=after,
                boot_id=metadata['boot_id'], time_namespace=metadata['time_namespace'],
                targets=targets)))
        (path / 'resource_samples.jsonl').write_text('\n'.join(
            json.dumps(x) for x in [metadata, *samples]) + '\n')
        (path / 'events.jsonl').write_text('\n'.join((
            json.dumps(dict(kind='barrier_release', start_monotonic_ns=start)),
            json.dumps(dict(kind='capture_end', monotonic_ns=time.monotonic_ns())))) + '\n')
        marker.write_text('capture ended')
        _, stderr = child.communicate(timeout=3)
        return dict(exit=child.returncode, stderr=stderr.decode(),
                    boundary_span_ns=after-before, result=trial(path))


passed = exercise()
missing = exercise(False)
assert passed['exit'] == 0 and passed['result']['status'] == 'PASS', passed
assert missing['result']['status'] == 'UNKNOWN' and missing['result']['reason'] == 'NO_CAPTURE_BOUNDARY'
result = dict(status='PASS_HOST_ONLY', measured_boundary=passed,
              missing_boundary=missing, gazebo_integrated=False)
(ROOT / 'analysis/q4_boundary_preflight.json').write_text(json.dumps(result, indent=2,
                                                             sort_keys=True) + '\n')
print(json.dumps(dict(status=result['status'], boundary_span_ns=passed['boundary_span_ns'],
                      measured=passed['result']['status'], missing=missing['result']['reason'])))
