"""Absolute-deadline Docker C-ID source: bind at capture, inject one fault at slot 50.

B1 I_FULL applies the shared binding/duplicate checks (cid_binding) and the
shared D5 R_EXPLICIT latch (d5_rearm) at the source: the check value is
recomputed from the OUTGOING wire, the reference is the capture-time binding.
A rejected sample's bytes are withheld with the verdict logged. B1 I_NATIVE
sees only the wire contract.
"""
import json
import os
import socket
import time
from pathlib import Path

import cid_fixture as fx
from cid_binding import Ingestion, binding_hash, check, projection, projection_from_wire
from d5_rearm import Rearm


def main():
    root = Path(os.environ['TRIAL_ROOT'])
    mode, regime, kind = os.environ['MODE'], os.environ['INFO_REGIME'], os.environ['CID_KIND']
    assert os.environ['CASE_ID'] == 'CID' and kind in fx.KINDS
    gate = Rearm('R_EXPLICIT') if (mode == 'b1' and regime == 'full') else None
    ingest = Ingestion()
    (root / 'sender.ready').write_text(f'C-ID source armed ({kind}); waiting for barrier\n')
    while not (root / 'barrier.json').exists():
        time.sleep(.005)
    start_ns = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
    sock = socket.create_connection(('127.0.0.1', 5005), timeout=5)
    (root / 'sender_transport.jsonl').write_text(json.dumps(dict(kind='connect', connection_index=1,
                                                                 monotonic_ns=time.monotonic_ns())) + '\n')
    verdicts = (root / 'gate_verdict.jsonl').open('a', buffering=1) if mode == 'b1' else None
    with (root / 'sent.jsonl').open('a', buffering=1) as output:
        for index in range(fx.SLOTS):
            scheduled_ns = start_ns + index * fx.PERIOD_NS
            while time.monotonic_ns() < scheduled_ns:
                time.sleep(max(0.0, min((scheduled_ns - time.monotonic_ns()) / 1e9, .001)))
            s = fx.spec(index)
            sample_ns = time.monotonic_ns()
            sid = fx.DUPLICATE_OF if (index == fx.INJECT_INDEX and kind == 'DUPLICATE_ID') else f'docker:{index}'
            native = {'isTracked': True}
            intended = projection(True, [s['x'], .2, .3], [0., 0., 0., 1.], s['teleop'], 1. if s['teleop'] else 0.)
            metadata = dict(sample_id=sid, generation_id=1, source_timestamp_ns=sample_ns, native_state=native,
                            phase=s['phase'], binding_version='XRROS-S4B-CIDQ1/binding-v1',
                            binding_sha256=binding_hash(sid, 1, sample_ns, native, intended))
            wire_x = s['x']
            injected = None
            if index == fx.INJECT_INDEX:
                injected = kind
                if kind == 'MISSING_FIELD':
                    metadata.pop('generation_id')
                elif kind == 'MISSING_ID':
                    metadata.pop('sample_id')
                elif kind == 'MISMATCH':
                    wire_x = fx.MISMATCH_X          # command payload differs from the bound state
            hand = {'isTracked': True, 'pos': {'x': wire_x, 'y': .2, 'z': .3},
                    'rot': {'x': 0., 'y': 0., 'z': 0., 'w': 1.}}
            payload = {'timestamp': sample_ns / 1e9, 'right_hand': hand,
                       'left_hand': {'isTracked': True, 'pos': {'x': .2, 'y': .2, 'z': .3},
                                     'rot': {'x': 0., 'y': 0., 'z': 0., 'w': 1.}},
                       'controls': {'right_teleop_enable': s['teleop'], 'teleop_enable': s['teleop'],
                                    'grip_value': 1. if s['teleop'] else 0., 'source': 'cp1_synthetic'},
                       '_qualification': metadata}
            wire = json.dumps(payload, separators=(',', ':')) + '\n'
            send_ns = time.monotonic_ns()
            allowed, reason = True, 'B0_OR_DOWNSTREAM_DECISION'
            if mode == 'b1':
                if gate is not None:
                    ok, reason = check(metadata, projection_from_wire(payload))
                    if ok:
                        ok, reason = ingest.observe(metadata['sample_id'], ('source', index))
                    if not ok:
                        gate._fault(send_ns, reason)
                        allowed = not s['teleop']
                    else:
                        allowed, reason = gate.sample(1, s['teleop'], True, sample_ns, send_ns, True)
                else:
                    allowed, reason = True, 'NATIVE_WIRE_ONLY_UNOBSERVABLE_BINDING'
                verdicts.write(json.dumps(dict(index=index, sample_id=metadata.get('sample_id'),
                    decision_monotonic_ns=send_ns, allowed=allowed, reason=reason, teleop=s['teleop'],
                    source_timestamp_ns=sample_ns, regime=regime, injected=injected)) + '\n')
            if allowed:
                sock.sendall(wire.encode())
            output.write(json.dumps(dict(index=index, phase=s['phase'], scheduled_ns=scheduled_ns, sent=bool(allowed),
                                         sample_ns=sample_ns, source_timestamp_ns=sample_ns, age_condition='A000',
                                         send_ns=send_ns, wire=wire, allowed=allowed, reason=reason,
                                         injected=injected, cid_kind=kind, connection_index=1)) + '\n')
    sock.close()
    (root / 'sender.done').write_text(f'{fx.SLOTS} planned slots; C-ID {kind}\n')


if __name__ == '__main__':
    main()
