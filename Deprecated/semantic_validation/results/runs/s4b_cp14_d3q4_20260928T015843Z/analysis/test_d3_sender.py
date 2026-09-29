"""No-Gazebo D3 sender fixture with an in-memory TCP socket substitute."""
import json
import os
import runpy
import socket
import sys
import tempfile
import time
from pathlib import Path

inputs = Path(__file__).resolve().parents[1] / 'inputs'
sys.path.insert(0, str(inputs))


class SocketSink:
    def __init__(self):
        self.lines = []
        self.closed = False

    def sendall(self, data):
        assert data.endswith(b'\n')
        self.lines.append(json.loads(data))

    def close(self):
        self.closed = True


def run():
    with tempfile.TemporaryDirectory(prefix='xrros_d3_sender_') as temp:
        root = Path(temp)
        start = time.monotonic_ns() + 100_000_000
        (root / 'barrier.json').write_text(json.dumps({'start_monotonic_ns': start}))
        os.environ.update(TRIAL_ROOT=str(root), MODE='b0', INFO_REGIME='full', CASE_ID='D3')
        sink = SocketSink()
        original = socket.create_connection
        socket.create_connection = lambda *_args, **_kwargs: sink
        try:
            runpy.run_path(str(inputs / 'd1_sender.py'), run_name='__main__')
        finally:
            socket.create_connection = original
        rows = [json.loads(line) for line in (root / 'sent.jsonl').read_text().splitlines()]
        assert len(rows) == 120 and [row['index'] for row in rows] == list(range(120))
        actual = [row for row in rows if row.get('sent')]
        silent = [row for row in rows if not row.get('sent')]
        assert len(actual) == len(sink.lines) == 100 and sink.closed
        assert [row['index'] for row in silent] == list(range(56, 76))
        assert all(row['wire'] is None and row['sample_ns'] is None and
                   row['send_ns'] is None and row['allowed'] is None for row in silent)
        assert sink.lines[55]['_qualification']['sample_id'] == 'docker:55'
        assert sink.lines[55]['right_hand']['isTracked'] is True
        assert sink.lines[55]['controls']['teleop_enable'] is True
        assert sink.lines[56]['_qualification']['sample_id'] == 'docker:76'
        assert all(row['right_hand']['isTracked'] is True for row in sink.lines)
        assert all(abs(row['send_ns'] - row['scheduled_ns']) <= 5_000_000 for row in actual)
        print('D3_SENDER_120_SLOTS_100_REAL_20_NO_BYTES_PASS')


if __name__ == '__main__':
    run()
