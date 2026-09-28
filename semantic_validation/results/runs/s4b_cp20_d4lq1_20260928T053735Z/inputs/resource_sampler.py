"""Observation-only 100 ms procfs sampler for the Q3 Docker qualification.

No ROS messages, validity fields, command contents or allow/deny decisions are read.
Missing processes/samples are explicit; no zero-value interpolation is made.
"""
import json
import os
import time
from pathlib import Path

ROOT = Path(os.environ.get('TRIAL_ROOT', '/results'))
PERIOD_NS = 100_000_000
HZ = os.sysconf('SC_CLK_TCK')
PAGE_SIZE = os.sysconf('SC_PAGE_SIZE')


def parse_stat(text):
    close = text.rfind(')')
    if close < 0:
        raise ValueError('malformed proc stat')
    pid = int(text.split('(', 1)[0].strip())
    fields = text[close + 2:].split()
    if len(fields) < 22:
        raise ValueError('short proc stat')
    return dict(pid=pid, state=fields[0], ppid=int(fields[1]),
                utime_ticks=int(fields[11]), stime_ticks=int(fields[12]),
                cutime_ticks=int(fields[13]), cstime_ticks=int(fields[14]),
                start_ticks=int(fields[19]), rss_pages=int(fields[21]))


def process_table():
    table = {}
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            row = parse_stat((path / 'stat').read_text())
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            continue
        table[row['pid']] = row
    return table


def descendants(table, root_pid):
    found = {root_pid}
    while True:
        more = {pid for pid, row in table.items() if row['ppid'] in found}
        if more <= found:
            break
        found |= more
    return sorted(pid for pid in found if pid in table)


def targets(root):
    result = {}
    for path in root.glob('participant_clock_*.json'):
        try:
            record = json.loads(path.read_text())
            if isinstance(record.get('pid'), int):
                result[record['label']] = record['pid']
        except (json.JSONDecodeError, KeyError):
            continue
    return result


def snapshot(root, identities):
    table = process_table()
    output = {}
    for label, pid in targets(root).items():
        if pid not in table:
            output[label] = dict(root_pid=pid, status='MISSING', processes=[])
            continue
        processes = []
        for child_pid in descendants(table, pid):
            row = table[child_pid].copy()
            key = (child_pid, row['start_ticks'])
            previous = identities.get(child_pid)
            if previous is not None and previous != row['start_ticks']:
                row['pid_reuse'] = True
            identities[child_pid] = row['start_ticks']
            row['cpu_time_seconds'] = (row['utime_ticks'] + row['stime_ticks']) / HZ
            row['child_waited_cpu_seconds'] = (row['cutime_ticks'] + row['cstime_ticks']) / HZ
            row['rss_bytes'] = row['rss_pages'] * PAGE_SIZE
            row['identity'] = [child_pid, row['start_ticks']]
            processes.append(row)
        output[label] = dict(root_pid=pid, status='OBSERVED', processes=processes)
    return output


def run(root=ROOT):
    root.mkdir(parents=True, exist_ok=True)
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    time_namespace = os.readlink('/proc/self/ns/time')
    identities = {}
    output = (root / 'resource_samples.jsonl').open('a', buffering=1)
    first = dict(kind='resource_metadata', monotonic_ns=time.monotonic_ns(),
                 boot_id=boot_id, time_namespace=time_namespace,
                 clock='CLOCK_MONOTONIC', period_ns=PERIOD_NS,
                 ticks_per_second=HZ, page_size=PAGE_SIZE)
    output.write(json.dumps(first, sort_keys=True) + '\n')
    start_ns = time.monotonic_ns()
    sample_index = 0
    while True:
        deadline_ns = start_ns + sample_index * PERIOD_NS
        now_ns = time.monotonic_ns()
        if now_ns < deadline_ns:
            time.sleep((deadline_ns - now_ns) / 1e9)
        observed_ns = time.monotonic_ns()
        record = dict(kind='sample', index=sample_index,
                      scheduled_ns=deadline_ns, monotonic_ns=observed_ns,
                      targets=snapshot(root, identities))
        output.write(json.dumps(record, sort_keys=True) + '\n')
        if sample_index == 0:
            (root / 'resource_sampler.ready').write_text(
                'first process snapshot written; CLOCK_MONOTONIC\n')
        sample_index += 1


if __name__ == '__main__':
    run()
