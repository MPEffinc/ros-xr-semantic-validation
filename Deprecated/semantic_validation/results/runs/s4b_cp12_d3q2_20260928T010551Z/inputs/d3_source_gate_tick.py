"""B1 source-side silence decision on the shared 50 Hz tick stream.

This is not the common stop adapter. It reads actual sender-source records;
planned no-byte slots and repeated ROS commands never update the receipt age.
"""
import json
import os
import time
from pathlib import Path

from d3_silence import SourceSilence

root = Path(os.environ['TRIAL_ROOT'])
assert os.environ['MODE'] == 'b1'
clock = SourceSilence()
source_offset = tick_offset = 0
fired = False
(root / 'd3_source_gate.ready').write_text('B1 source-side tick gate awaiting barrier\n')
while not (root / 'barrier.json').exists():
    time.sleep(.005)

with (root / 'd3_gate_ticks.jsonl').open('a', buffering=1) as output:
    while True:
        ticks = root / 'd3_ticks.jsonl'
        if not ticks.exists():
            time.sleep(.002)
            continue
        with ticks.open() as stream:
            stream.seek(tick_offset)
            while True:
                line = stream.readline()
                if not line or not line.endswith('\n'):
                    break
                tick_offset = stream.tell()
                tick = json.loads(line)
                # Consume only real source records that completed before this
                # tick. The original source order and receipt clock are kept.
                sent = root / 'sent.jsonl'
                if sent.exists():
                    with sent.open() as source_stream:
                        source_stream.seek(source_offset)
                        while True:
                            position = source_stream.tell()
                            source_line = source_stream.readline()
                            if not source_line or not source_line.endswith('\n'):
                                break
                            row = json.loads(source_line)
                            if row.get('send_ns') is not None and row['send_ns'] > tick['tick_monotonic_ns']:
                                source_offset = position
                                break
                            source_offset = source_stream.tell()
                            if not row.get('sent'):
                                continue
                            payload = json.loads(row['wire'])
                            meta = payload['_qualification']
                            clock.receive(meta['sample_id'], row['send_ns'],
                                          payload['controls']['teleop_enable'],
                                          meta['native_state']['isTracked'],
                                          meta['generation_id'])
                result = clock.tick(tick['tick_monotonic_ns'])
                record = dict(tick_id=tick['tick_id'],
                              tick_monotonic_ns=tick['tick_monotonic_ns'],
                              **result)
                output.write(json.dumps(record, sort_keys=True) + '\n')
                first_detection = result['state'] == 'SOURCE_SILENCE' and not fired
                if first_detection:
                    fired = True
                with (root / 'gate_verdict.jsonl').open('a', buffering=1) as verdict:
                    verdict.write(json.dumps(dict(kind='b1_source_silence_tick',
                        index=None, sample_id=None, parent_sample_id=result['last_sample_id'],
                        decision_monotonic_ns=time.monotonic_ns(),
                        allowed=result['state'] != 'SOURCE_SILENCE',
                        reason=result['state'], first_detection=first_detection,
                        trigger_monotonic_ns=result['trigger_ns'],
                        tick_id=tick['tick_id'], source_clock='CLOCK_MONOTONIC')) + '\n')
        if (root / 'd3_tick.done').exists() and tick_offset == ticks.stat().st_size:
            (root / 'd3_source_gate.done').write_text('all 300 common ticks evaluated\n')
            break
        time.sleep(.002)
while True:
    time.sleep(.1)
