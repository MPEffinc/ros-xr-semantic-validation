"""Trial-owned C-MON fault injector (runs INSIDE the trial container only).

Faults (CMON_FAULT):
  ORACLE_ABSENT         the official oracle was never started (launch.sh); this
                        process proves absence: no oracle PID file, the oracle port
                        refuses connections before the barrier and at the fault time.
  ORACLE_DISCONNECT     at slot 45 (moving, valid source continuing) SIGKILL the
                        official TLOracle process after proving it is healthy.
  ORACLE_NONRESPONSIVE  same time: SIGSTOP the oracle (process alive, no replies;
                        the official monitor's 50 ms socket timeout applies).
  B1_GATE_FAIL / B3_GATE_FAIL  same time: write the gate-failure marker; the gate
                        component stops producing verdicts and passes input
                        through (fail-open crash model); the common 250 ms verdict
                        heartbeat watchdog is what may react.
Ownership: the target PID must be this container's own oracle, identified by the
PID file written at its exec and by /proc/<pid>/cmdline; the container PID
namespace makes host or laboratory processes unreachable.
"""
import json
import os
import signal
import socket
import time
from pathlib import Path

root = Path(os.environ['TRIAL_ROOT'])
fault = os.environ['CMON_FAULT']
FAULT_SLOT = 45
assert fault in ('ORACLE_ABSENT', 'ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE', 'B1_GATE_FAIL', 'B3_GATE_FAIL')
log = (root / 'cmon_fault.jsonl').open('a', buffering=1)


def emit(kind, **data):
    log.write(json.dumps(dict(kind=kind, fault=fault, monotonic_ns=time.monotonic_ns(), **data), sort_keys=True) + '\n')


def port_refuses():
    port_file = root / 'oracle.port'
    if not port_file.exists():
        return None
    try:
        with socket.create_connection(('127.0.0.1', int(port_file.read_text())), timeout=.2):
            return False
    except OSError:
        return True


def oracle_identity():
    pid = int((root / 'oracle.pid').read_text())
    cmd = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode()
    state = Path(f'/proc/{pid}/stat').read_text().split(')')[-1].split()[0]
    return pid, cmd, state


def property_rows():
    p = root / 'property.jsonl'
    return sum(1 for _ in p.open()) if p.exists() else 0


(root / 'cmon_fault.ready').write_text(fault + '\n')
emit('armed', oracle_pid_file=(root / 'oracle.pid').exists(), oracle_port_refuses=port_refuses())
while not (root / 'barrier.json').exists():
    time.sleep(.005)
start_ns = json.loads((root / 'barrier.json').read_text())['start_monotonic_ns']
due = start_ns + FAULT_SLOT * 50_000_000
while time.monotonic_ns() < due:
    time.sleep(.001)
if fault == 'ORACLE_ABSENT':
    emit('absence_proof', oracle_pid_file=(root / 'oracle.pid').exists(), oracle_port_refuses=port_refuses())
elif fault in ('ORACLE_DISCONNECT', 'ORACLE_NONRESPONSIVE'):
    pid, cmd, state = oracle_identity()
    owned = 'TLOracle/oracle.py' in cmd and '--property d3_tloracle_property' in cmd
    before = property_rows()
    time.sleep(.1)
    after = property_rows()
    emit('pre_fault_health', pid=pid, cmdline=cmd, state=state, owned=owned,
         property_rows_100ms_before=before, property_rows_at_fault=after, healthy=owned and after > before)
    if not owned:
        emit('refused_not_owned', pid=pid)
        raise SystemExit(3)
    sig = signal.SIGKILL if fault == 'ORACLE_DISCONNECT' else signal.SIGSTOP
    os.kill(pid, sig)
    injected_ns = time.monotonic_ns()
    time.sleep(.05)
    exists = Path(f'/proc/{pid}').exists()
    post_state = Path(f'/proc/{pid}/stat').read_text().split(')')[-1].split()[0] if exists else None
    emit('injected', pid=pid, signal=sig.name, injected_monotonic_ns=injected_ns,
         process_exists_after_50ms=exists, process_state_after_50ms=post_state)
else:
    marker = root / ('b1_gate_failed' if fault == 'B1_GATE_FAIL' else 'b3_check_failed')
    marker.write_text(str(time.monotonic_ns()) + '\n')
    emit('injected', marker=marker.name, injected_monotonic_ns=int(marker.read_text()))
(root / 'cmon_fault.done').write_text(fault + '\n')
while True:
    time.sleep(.5)
