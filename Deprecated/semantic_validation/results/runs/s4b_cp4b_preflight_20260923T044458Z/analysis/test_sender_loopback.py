"""Non-Gazebo CP4 sender preflight; does not score a defense baseline."""
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENDER = ROOT / 'inputs/d1_sender.py'
EXPECTED_FIXTURE_SHA256 = '20dcbc12db4f54f3660f00662ed554c220a5de35ba1b2116d40e727ba83c918b'


def run_sender(trial, server):
    trial.mkdir()
    start = time.monotonic_ns() + 1_000_000_000
    (trial / 'barrier.json').write_text(json.dumps({'start_monotonic_ns': start}))
    env = os.environ.copy()
    env.update(TRIAL_ROOT=str(trial), MODE='b2', INFO_REGIME='full')
    captured = []
    if server:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', 5005))
        sock.listen(1)
        def collect():
            peer, _ = sock.accept()
            with peer.makefile('r') as stream:
                captured.extend(line for line in stream)
            peer.close()
        thread = threading.Thread(target=collect, daemon=True)
        thread.start()
    result = subprocess.run([sys.executable, str(SENDER)], env=env,
                            capture_output=True, text=True, timeout=14)
    if server:
        thread.join(timeout=3)
        sock.close()
        assert not thread.is_alive(), 'TCP receiver did not close'
    (ROOT / 'stdout' / f'sender_{trial.name}.log').write_text(result.stdout)
    (ROOT / 'stderr' / f'sender_{trial.name}.log').write_text(result.stderr)
    return result, captured, start


with tempfile.TemporaryDirectory(prefix='s4b_cp4_sender_') as temp:
    base = Path(temp)
    result, captured, start = run_sender(base / 'complete', True)
    records = [json.loads(line) for line in (base / 'complete/sent.jsonl').read_text().splitlines()]
    assert result.returncode == 0, result.stderr
    assert len(records) == len(captured) == 120
    assert [r['index'] for r in records] == list(range(120))
    assert (base / 'complete/sender.done').exists()
    assert [json.loads(x) for x in captured] == [json.loads(r['wire']) for r in records]
    normalized = []
    for row in records:
        wire = json.loads(row['wire'])
        wire.pop('timestamp', None)
        wire['_qualification'].pop('source_timestamp_ns', None)
        normalized.append(wire)
    fixture_sha = hashlib.sha256(json.dumps(normalized, sort_keys=True,
                                            separators=(',', ':')).encode()).hexdigest()
    assert fixture_sha == EXPECTED_FIXTURE_SHA256, fixture_sha
    offsets_ms = [(r['sample_ns'] - start - r['index'] * 50_000_000) / 1e6 for r in records]
    late_ms = [max(0.0, v) for v in offsets_ms]
    assert max(abs(v) for v in offsets_ms) <= 5.0, max(offsets_ms)
    failed, _, _ = run_sender(base / 'closed_socket', False)
    assert failed.returncode != 0
    assert not (base / 'closed_socket/sender.done').exists()
    summary = dict(status='PASS_NON_GAZEBO_PREFLIGHT', source_count=120,
                   indices_unique=True, fixture_sha256=fixture_sha,
                   max_abs_schedule_offset_ms=max(abs(v) for v in offsets_ms),
                   max_lateness_ms=max(late_ms),
                   late_over_5ms_count=sum(v > 5 for v in late_ms),
                   closed_socket_exit=failed.returncode,
                   failed_sender_done=False,
                   caveat='Host loopback only; real ROS/Gazebo timing remains unverified')
    (ROOT / 'analysis/sender_loopback.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, sort_keys=True))
