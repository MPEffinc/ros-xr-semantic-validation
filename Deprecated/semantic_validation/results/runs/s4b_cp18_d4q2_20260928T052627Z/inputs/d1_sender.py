"""Absolute-deadline Docker D4 source fixture, separate from the ROS recorder.

D4Q1: the registered D1 motion shape (idle 0-19, reference 20-35, active 36-55
at x=.35, teleop-false tail 56-119) with ONE registered source-timestamp
condition per trial. Each sample's stamp is derived from its own creation time
(d4_age.stamp), except the literal historical epoch value 1.0 s. All 120 slots
are real samples; only a B1 source-side rejection withholds bytes, and that
withholding is logged with the rejecting verdict.

D4Q2: the ORIGINAL receiver closes a client after 1.5 s without bytes
(client_idle_disconnect_sec). A B1 rejection run of samples 20-55 lasts 1.8 s,
so before each real transmission the sender checks for a peer-closed socket and
reconnects, logging every reconnect in sender_transport.jsonl. The payload,
stamp and schedule are unchanged; no retransmission of any sample.
"""
import select
import json
import os
import socket
import time
from pathlib import Path
from d1_contract import FRESHNESS_NS, d1_allow
from d4_age import condition_from_env, stamp

root = Path(os.environ['TRIAL_ROOT'])
mode = os.environ['MODE']
regime = os.environ['INFO_REGIME']
assert os.environ['CASE_ID'] == 'D4', 'this prospective sender is D4 only'
condition = condition_from_env()
(root / 'sender.ready').write_text(f'source index 0 armed; D4 {condition}; waiting for barrier\n')
while not (root / 'barrier.json').exists():
    time.sleep(.005)
start_ns = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
sock = socket.create_connection(('127.0.0.1', 5005), timeout=5)
connection_index = 1
transport = (root / 'sender_transport.jsonl').open('a', buffering=1)
transport.write(json.dumps(dict(kind='connect', connection_index=1,
                                monotonic_ns=time.monotonic_ns())) + '\n')


def peer_closed(current):
    readable, _, _ = select.select([current], [], [], 0)
    if not readable:
        return False
    try:
        return current.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT) == b''
    except (BlockingIOError, InterruptedError):
        return False
    except OSError:
        return True
with (root / 'sent.jsonl').open('a', buffering=1) as output:
    for index in range(120):
        scheduled_ns = start_ns + index * 50_000_000
        while time.monotonic_ns() < scheduled_ns:
            remaining = (scheduled_ns - time.monotonic_ns()) / 1e9
            time.sleep(max(0.0, min(remaining, .001)))
        phase = 'idle' if index < 20 else 'reference' if index < 36 else 'active' if index < 56 else 'tail'
        teleop = phase in ('reference', 'active')
        x = .35 if phase == 'active' else .2
        tracked = True
        sample_ns = time.monotonic_ns()
        source_ns = stamp(condition, sample_ns)
        metadata = dict(sample_id=f'docker:{index}', generation_id=1,
                        source_timestamp_ns=source_ns,
                        native_state={'isTracked': tracked}, phase=phase)
        hand = {'isTracked': tracked, 'pos': {'x': x, 'y': .2, 'z': .3},
                'rot': {'x': 0., 'y': 0., 'z': 0., 'w': 1.}}
        payload = {'timestamp': source_ns / 1e9, 'right_hand': hand,
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
                    source_timestamp_ns=source_ns, freshness_ns=FRESHNESS_NS,
                    regime=regime))+'\n')
        if allowed:
            if peer_closed(sock):
                sock.close()
                sock = socket.create_connection(('127.0.0.1', 5005), timeout=5)
                connection_index += 1
                transport.write(json.dumps(dict(kind='reconnect_after_peer_close',
                    connection_index=connection_index, before_index=index,
                    monotonic_ns=time.monotonic_ns())) + '\n')
            sock.sendall(wire.encode())
        output.write(json.dumps(dict(index=index, phase=phase, scheduled_ns=scheduled_ns, sent=bool(allowed),
                                     sample_ns=sample_ns, source_timestamp_ns=source_ns,
                                     age_condition=condition, send_ns=send_ns, wire=wire,
                                     allowed=allowed, reason=reason,
                                     connection_index=connection_index)) + '\n')
sock.close()
(root / 'sender.done').write_text(f'120 planned real source slots; D4 {condition}\n')
