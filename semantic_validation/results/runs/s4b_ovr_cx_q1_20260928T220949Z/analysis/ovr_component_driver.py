"""No-Gazebo component driver: stands in ONLY for the recorder's barrier/ACK role.

Waits for production.ready (B2: for one calibration envelope observed at the
official property, forwarded status and stripper receipt, then writes
calibration.ack), releases a barrier 0.5 s later, and exits after 12.5 s.
"""
import json
import os
import time
from pathlib import Path

root = Path(os.environ['TRIAL_ROOT'])
mode = os.environ['MODE']


def rows(p):
    try:
        return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()] if Path(p).exists() else []
    except json.JSONDecodeError:
        return []


limit = time.monotonic() + 60
while time.monotonic() < limit and not (root / 'production.ready').exists():
    time.sleep(.05)
if mode == 'b2':
    while time.monotonic() < limit:
        keys = {a['key'] for a in rows(root / 'calibration.jsonl')}
        rec = {r.get('monitor_event_id') for r in rows(root / 'lineage.jsonl') if r.get('kind') == 'monitor_output_received'}
        props = {p.get('monitor_event_id') for p in rows(root / 'property.jsonl')}
        hit = keys & rec & props
        if hit:
            (root / 'calibration.ack').write_text(json.dumps(dict(key=sorted(hit)[0])) + '\n')
            break
        time.sleep(.05)
start = time.monotonic_ns() + 500_000_000
(root / 'barrier.json').write_text(json.dumps(dict(start_monotonic_ns=start)))
time.sleep(13.0)
