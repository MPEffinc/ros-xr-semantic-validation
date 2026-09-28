"""Absolute-deadline Docker source fixture, separate from the ROS recorder."""
import json
import os
import socket
import time
from pathlib import Path

root = Path(os.environ['TRIAL_ROOT'])
(root / 'sender.ready').write_text('source index 0 armed; waiting for barrier\n')
while not (root / 'barrier.json').exists():
    time.sleep(.005)
start_ns = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
sock = socket.create_connection(('127.0.0.1', 5005), timeout=5)
with (root / 'sent.jsonl').open('a', buffering=1) as output:
    for index in range(120):
        scheduled_ns = start_ns + index * 50_000_000
        while time.monotonic_ns() < scheduled_ns:
            remaining = (scheduled_ns - time.monotonic_ns()) / 1e9
            time.sleep(min(remaining, .001))
        phase = 'idle' if index < 20 else 'reference' if index < 36 else 'active' if index < 56 else 'tail'
        teleop = phase in ('reference', 'active')
        x = .35 if phase == 'active' else .2
        sample_ns = time.monotonic_ns()
        metadata = dict(sample_id=f'docker:{index}', generation_id=1,
                        source_timestamp_ns=sample_ns,
                        native_state={'isTracked': True}, phase=phase)
        hand = {'isTracked': True, 'pos': {'x': x, 'y': .2, 'z': .3},
                'rot': {'x': 0., 'y': 0., 'z': 0., 'w': 1.}}
        payload = {'timestamp': sample_ns / 1e9, 'right_hand': hand,
                   'left_hand': {'isTracked': True, 'pos': {'x': .2, 'y': .2, 'z': .3},
                                 'rot': {'x': 0., 'y': 0., 'z': 0., 'w': 1.}},
                   'controls': {'right_teleop_enable': teleop, 'teleop_enable': teleop,
                                'grip_value': 1. if teleop else 0., 'source': 'cp1_synthetic'},
                   '_qualification': metadata}
        wire = json.dumps(payload, separators=(',', ':')) + '\n'
        send_ns = time.monotonic_ns()
        sock.sendall(wire.encode())
        output.write(json.dumps(dict(index=index, phase=phase, scheduled_ns=scheduled_ns,
                                     sample_ns=sample_ns, send_ns=send_ns, wire=wire)) + '\n')
sock.close()
