"""Observation-only clock identity immediately before exec of a trial process."""
import json
import os
import sys
import time
from pathlib import Path

label, *argv = sys.argv[1:]
if not label or not argv:
    raise SystemExit(2)
root = Path(os.environ['TRIAL_ROOT'])
record = dict(label=label, pid=os.getpid(),
              boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              time_namespace=os.readlink('/proc/self/ns/time'),
              clock='CLOCK_MONOTONIC', monotonic_ns=time.monotonic_ns(),
              argv=argv)
(root / f'participant_clock_{label}.json').write_text(json.dumps(record, sort_keys=True) + '\n')
os.execvp(argv[0], argv)
