"""Observation-only parent for a finite sender; no source or policy reads.

The child runs its original argv unchanged. wait4 records final kernel rusage.
The parent remains sampleable until an explicit capture-end marker, without
extending the child's transmission lifetime. This is a Q4 candidate only.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def identity(pid):
    stat = Path(f'/proc/{pid}/stat').read_text()
    fields = stat[stat.rfind(')') + 2:].split()
    return [pid, int(fields[19])]


def run(argv):
    marker = Path(os.environ['XR_CAPTURE_END_MARKER'])
    output = Path(os.environ['XR_SENDER_ACCOUNTING'])
    child = subprocess.Popen(argv)
    start_ns = time.monotonic_ns()
    child_identity = identity(child.pid)
    pid, status, usage = os.wait4(child.pid, 0)
    wait_return_ns = time.monotonic_ns()
    exit_code = os.waitstatus_to_exitcode(status)
    record = dict(schema='XRROS-S4B-Q4/sender-lifecycle-v1',
                  clock='CLOCK_MONOTONIC', boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  time_namespace=os.readlink('/proc/self/ns/time'),
                  parent_identity=identity(os.getpid()), child_identity=child_identity,
                  child_argv=argv, child_start_upper_bound_ns=start_ns,
                  wait4_return_ns=wait_return_ns, raw_wait_status=status,
                  child_exit_code=exit_code, child_cpu_user_seconds=usage.ru_utime,
                  child_cpu_system_seconds=usage.ru_stime,
                  child_maxrss_kib=usage.ru_maxrss,
                  child_exit_exact_ns=None,
                  child_exit_time_note='wait4 return is an upper bound, not kernel exit timestamp',
                  maxrss_note='kernel peak RSS, not RSS at exit')
    output.write_text(json.dumps(record, sort_keys=True) + '\n')
    if exit_code != 0:
        return exit_code
    # Parent existence is for procfs observation only. No sender command runs here.
    while not marker.exists():
        time.sleep(0.005)
    return 0


if __name__ == '__main__':
    if not sys.argv[1:]:
        raise SystemExit('usage: wrapper.py CHILD [ARGS...]')
    raise SystemExit(run(sys.argv[1:]))
