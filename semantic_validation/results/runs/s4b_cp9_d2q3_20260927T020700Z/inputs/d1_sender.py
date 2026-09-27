"""Absolute-deadline Docker source fixture, separate from the ROS recorder."""
import json
import os
import socket
import time
from pathlib import Path
from d1_contract import d1_allow

root = Path(os.environ['TRIAL_ROOT'])
mode = os.environ['MODE']
regime = os.environ['INFO_REGIME']
assert os.environ['CASE_ID'] == 'D2', 'this prospective sender is D2 only'
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
            time.sleep(max(0.0, min(remaining, .001)))
        phase = ('idle' if index < 20 else 'reference' if index < 36 else
                 'active' if index < 56 else 'fault_window' if index < 76 else 'tail')
        teleop = phase in ('reference', 'active', 'fault_window')
        x = .35 if phase in ('active', 'fault_window') else .2
        tracked = phase != 'fault_window'
        sample_ns = time.monotonic_ns()
        metadata = dict(sample_id=f'docker:{index}', generation_id=1,
                        source_timestamp_ns=sample_ns,
                        native_state={'isTracked': tracked}, phase=phase)
        hand = {'isTracked': tracked, 'pos': {'x': x, 'y': .2, 'z': .3},
                'rot': {'x': 0., 'y': 0., 'z': 0., 'w': 1.}}
        payload = {'timestamp': sample_ns / 1e9, 'right_hand': hand,
                   'left_hand': {'isTracked': True, 'pos': {'x': .2, 'y': .2, 'z': .3},
                                 'rot': {'x': 0., 'y': 0., 'z': 0., 'w': 1.}},
                   'controls': {'right_teleop_enable': teleop, 'teleop_enable': teleop,
                                'grip_value': 1. if teleop else 0., 'source': 'cp1_synthetic'},
                   '_qualification': metadata}
        wire = json.dumps(payload, separators=(',', ':')) + '\n'
        send_ns = time.monotonic_ns()
        allowed = True
        reason = 'B0_OR_DOWNSTREAM_DECISION'
        if mode == 'b1':
            if regime == 'full' and teleop:
                allowed, reason = d1_allow(metadata['native_state'], teleop,
                                           metadata['source_timestamp_ns'], send_ns,
                                           metadata['generation_id'])
            elif regime == 'native':
                allowed = not teleop or hand['isTracked']
                reason = 'NATIVE_WIRE_ONLY_UNOBSERVABLE_TIME_GENERATION'
            else:
                reason = 'INTENTIONAL_UNGRIPPED_NEUTRAL'
            with (root / 'gate_verdict.jsonl').open('a') as verdict_file:
                verdict_file.write(json.dumps(dict(index=index, sample_id=metadata['sample_id'],
                    decision_monotonic_ns=send_ns, allowed=allowed, reason=reason,
                    regime=regime))+'\n')
        if allowed:
            sock.sendall(wire.encode())
        output.write(json.dumps(dict(index=index, phase=phase, scheduled_ns=scheduled_ns,
                                     sample_ns=sample_ns, send_ns=send_ns, wire=wire,
                                     allowed=allowed, reason=reason)) + '\n')
sock.close()
(root / 'sender.done').write_text('120 source indices attempted\n')
