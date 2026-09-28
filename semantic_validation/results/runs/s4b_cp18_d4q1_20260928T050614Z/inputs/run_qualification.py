"""Run the frozen D4Q1 setup schedule; at most two pre-barrier-only setup retries.

A retry (<id>_setup02/_setup03) is allowed only when an attempt produced no
barrier.json, i.e. before any source sample or outcome existed.
"""
import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--start', type=int, required=True)
parser.add_argument('--end', type=int, required=True)
args = parser.parse_args()
schedule = list(csv.DictReader((ROOT / 'qualification_schedule.csv').open()))
for row in schedule[args.start - 1:args.end]:
    for suffix in ('', '_setup02', '_setup03'):
        attempt = 'd4q1s01' + suffix
        argv = [sys.executable, str(ROOT / 'inputs/run_owned.py'), 'docker', row['mode'],
                '--regime', row['regime'], '--attempt', attempt,
                '--condition', row['condition'], '--profile', row['profile']]
        if row['composed'] == '1':
            argv.append('--composed')
        rc = subprocess.run(argv).returncode
        name = row['trial_id'] + suffix
        reached = (ROOT / 'raw' / name / 'barrier.json').exists()
        with (ROOT / 'attempts.jsonl').open('a') as f:
            f.write(json.dumps(dict(order=int(row['order']), trial_id=row['trial_id'], attempt=name,
                                    runner_exit=rc, reached_start_barrier=reached,
                                    time_ns=time.time_ns()), sort_keys=True) + '\n')
        print('END', row['order'], name, rc, reached, flush=True)
        if reached or rc == 0:
            break
    else:
        raise SystemExit(f'SETUP_RETRIES_EXHAUSTED {row["trial_id"]}')
