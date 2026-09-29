"""Absolute-deadline Docker D5 source: moving disconnect, generation 2, old-gen replay.

The source closes its TCP connection at slot 56 (moving) and opens a new one at
slot 70 (0.7 s later) with generation 2. Every real sample carries its own
fresh stamp, generation, sample ID and state in `_qualification`. B1 I_FULL
applies the shared d5_rearm policy at the source: the disconnect is observed
locally at close time, and a rejected sample's bytes are withheld with the
verdict logged. B1 I_NATIVE sees only the wire contract (no generation/time).
"""
import json
import os
import select
import socket
import time
from pathlib import Path

import importlib

from d5_rearm import Rearm


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


def main():
    root = Path(os.environ['TRIAL_ROOT'])
    mode, regime = os.environ['MODE'], os.environ['INFO_REGIME']
    policy = os.environ['XR_REARM_POLICY']
    assert os.environ['CASE_ID'] in ('D5', 'D6')
    # D6Q1: the same sender drives the D6 fixture (no close/reconnect/replay).
    fx = importlib.import_module('d6_fixture' if os.environ['CASE_ID'] == 'D6' else 'd5_fixture')
    gate = Rearm(policy) if (mode == 'b1' and regime == 'full') else None
    (root / 'sender.ready').write_text(f'D5 source armed ({policy}); waiting for barrier\n')
    while not (root / 'barrier.json').exists():
        time.sleep(.005)
    start_ns = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
    transport = (root / 'sender_transport.jsonl').open('a', buffering=1)
    verdicts = (root / 'gate_verdict.jsonl').open('a', buffering=1) if mode == 'b1' else None
    sock = socket.create_connection(('127.0.0.1', 5005), timeout=5)
    connection_index = 1
    transport.write(json.dumps(dict(kind='connect', connection_index=1, monotonic_ns=time.monotonic_ns())) + '\n')
    with (root / 'sent.jsonl').open('a', buffering=1) as output:
        for index in range(fx.SLOTS):
            scheduled_ns = start_ns + index * fx.PERIOD_NS
            while time.monotonic_ns() < scheduled_ns:
                time.sleep(max(0.0, min((scheduled_ns - time.monotonic_ns()) / 1e9, .001)))
            s = fx.spec(index)
            if fx.CLOSE_INDEX is not None and index == fx.CLOSE_INDEX:
                sock.close()
                close_ns = time.monotonic_ns()
                transport.write(json.dumps(dict(kind='source_close_while_moving', connection_index=connection_index,
                                                monotonic_ns=close_ns)) + '\n')
                if gate is not None:
                    gate.disconnect(close_ns)
                    verdicts.write(json.dumps(dict(kind='b1_disconnect', index=index, sample_id=None,
                        decision_monotonic_ns=close_ns, allowed=False, reason='DISCONNECTED',
                        policy=policy, regime=regime)) + '\n')
            if fx.RECONNECT_INDEX is not None and index == fx.RECONNECT_INDEX:
                sock = socket.create_connection(('127.0.0.1', 5005), timeout=5)
                connection_index += 1
                transport.write(json.dumps(dict(kind='connect_new_generation', connection_index=connection_index,
                                                generation=2, monotonic_ns=time.monotonic_ns())) + '\n')
            if not s['sent']:
                output.write(json.dumps(dict(index=index, phase=s['phase'], scheduled_ns=scheduled_ns, sent=False,
                                             sample_ns=None, source_timestamp_ns=None, send_ns=None, wire=None,
                                             allowed=None, reason='INTENTIONAL_DISCONNECTED_NO_BYTES',
                                             connection_index=None)) + '\n')
                continue
            sample_ns = time.monotonic_ns()
            tracked = s.get('tracked', True)
            metadata = dict(sample_id=f'docker:{index}', generation_id=s['generation'],
                            source_timestamp_ns=sample_ns, native_state={'isTracked': tracked}, phase=s['phase'])
            hand = {'isTracked': tracked, 'pos': {'x': s['x'], 'y': .2, 'z': .3},
                    'rot': {'x': 0., 'y': 0., 'z': 0., 'w': 1.}}
            teleop = s['teleop']
            payload = {'timestamp': sample_ns / 1e9, 'right_hand': hand,
                       'left_hand': {'isTracked': True, 'pos': {'x': .2, 'y': .2, 'z': .3},
                                     'rot': {'x': 0., 'y': 0., 'z': 0., 'w': 1.}},
                       'controls': {'right_teleop_enable': teleop, 'teleop_enable': teleop,
                                    'grip_value': 1. if teleop else 0., 'source': 'cp1_synthetic'},
                       '_qualification': metadata}
            wire = json.dumps(payload, separators=(',', ':')) + '\n'
            send_ns = time.monotonic_ns()
            allowed, reason = True, 'B0_OR_DOWNSTREAM_DECISION'
            if mode == 'b1':
                if gate is not None:
                    allowed, reason = gate.sample(s['generation'], teleop, tracked, sample_ns, send_ns, True)
                else:
                    allowed, reason = (not teleop or hand['isTracked']), 'NATIVE_WIRE_ONLY_UNOBSERVABLE_TIME_GENERATION'
                verdicts.write(json.dumps(dict(index=index, sample_id=metadata['sample_id'],
                    decision_monotonic_ns=send_ns, allowed=allowed, reason=reason, teleop=teleop,
                    generation_id=s['generation'], source_timestamp_ns=sample_ns, policy=policy,
                    regime=regime, armed_after=None if gate is None else gate.armed)) + '\n')
            if allowed:
                if peer_closed(sock):
                    sock.close()
                    sock = socket.create_connection(('127.0.0.1', 5005), timeout=5)
                    connection_index += 1
                    transport.write(json.dumps(dict(kind='reconnect_after_peer_close', connection_index=connection_index,
                                                    before_index=index, monotonic_ns=time.monotonic_ns())) + '\n')
                sock.sendall(wire.encode())
            output.write(json.dumps(dict(index=index, phase=s['phase'], scheduled_ns=scheduled_ns, sent=bool(allowed),
                                         sample_ns=sample_ns, source_timestamp_ns=sample_ns, age_condition='A000',
                                         send_ns=send_ns, wire=wire, allowed=allowed, reason=reason,
                                         generation_id=s['generation'], connection_index=connection_index)) + '\n')
    sock.close()
    if gate is not None:
        (root / 'b1_rearm_events.json').write_text(json.dumps(gate.events, sort_keys=True) + '\n')
    (root / 'sender.done').write_text(f"{fx.SLOTS} planned slots; {os.environ['CASE_ID']} {policy}\n")


if __name__ == '__main__':
    main()
