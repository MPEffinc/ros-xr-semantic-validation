#!/usr/bin/env python3
"""Append raw-capture entries to manifests/dataset_manifest.csv (sha256 + size); raw files stay out of Git.

Usage: make_manifest.py <manifest.csv> <trial> <task> <session> <operator> <capture_point> <net_condition> <provenance> <raw_path>
provenance: REAL | UPSTREAM | SYNTHETIC | PIPELINE_TEST
"""
import csv, datetime, hashlib, os, sys
cols = ['trial', 'task', 'session', 'operator', 'timestamp_utc', 'raw_path', 'size_bytes', 'sha256',
        'capture_point', 'network_condition', 'provenance']
man, trial, task, sess, op, cp, net, prov, raw = sys.argv[1:10]
h = hashlib.sha256(open(raw, 'rb').read()).hexdigest()
new = not os.path.exists(man)
with open(man, 'a', newline='') as f:
    w = csv.writer(f)
    if new: w.writerow(cols)
    w.writerow([trial, task, sess, op, datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
                raw, os.path.getsize(raw), h, cp, net, prov])
print(h)
