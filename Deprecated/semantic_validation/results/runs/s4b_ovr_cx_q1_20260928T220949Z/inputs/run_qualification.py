"""Run the frozen OpenVR Q1 setup schedule sequentially (no concurrent load).

A setup retry (<id>_setup02/_setup03, identical parameters) is made ONLY when an
attempt produced no start barrier. A trial that reached the barrier is final.
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('--start', type=int, required=True)
ap.add_argument('--end', type=int, required=True)
a = ap.parse_args()
rows = list(csv.DictReader((ROOT / 'qualification_schedule.csv').open()))
for row in rows[a.start - 1:a.end]:
    reached = False
    for suffix in ('', '_setup02', '_setup03'):
        attempt = 'cxq1s01' + suffix
        argv = [sys.executable, str(ROOT / 'inputs/run_owned.py'), row['mode'], '--case', 'NONE',
                '--rearm', 'R_EXPLICIT', '--attempt', attempt, '--cid-kind', row['cid_kind'], '--fault', row['fault']]
        if row['composed'] == '1':
            argv.append('--composed')
        if row.get('st') == '1':
            argv.append('--st')
        rc = subprocess.run(argv).returncode
        variant = row['baseline']
        tag = row['cid_kind'] if row['cid_kind'] != 'NONE' else row['fault']
        trial = ROOT / 'raw' / f"openvr_{variant}_full_{tag}_{attempt}"
        reached = (trial / 'barrier.json').exists()
        print('END', row['order'], trial.name, rc, reached, flush=True)
        if reached:
            break
    if not reached:
        print('SETUP_RETRIES_EXHAUSTED', row['order'], flush=True)
        raise SystemExit(0)
