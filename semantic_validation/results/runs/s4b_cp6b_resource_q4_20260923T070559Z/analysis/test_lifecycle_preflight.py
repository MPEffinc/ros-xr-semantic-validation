"""Host-only A-I preflight of finite sender accounting; never starts ROS/Gazebo."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
Q3_INPUTS = HERE.parent / 'inputs'
sys.path.insert(0, str(Q3_INPUTS))
from resource_sampler import snapshot, HZ, PERIOD_NS  # noqa: E402
from lifecycle_resource_audit import assess  # noqa: E402

CHILD = '''import subprocess,sys,time
duration=float(sys.argv[1]);mode=sys.argv[2]
if mode == "descendant":
    subprocess.run([sys.executable,"-c","import time; t=time.monotonic()+.12; exec('while time.monotonic()<t: pass')"],check=True)
deadline=time.monotonic()+duration
while time.monotonic()<deadline: pass
sys.exit(7 if mode == "abnormal" else 0)
'''


def scenario(name, duration, mode='normal', capture_s=.55):
    with tempfile.TemporaryDirectory(prefix='xr_cp6a_') as temp:
        root = Path(temp)
        marker, accounting = root / 'capture_end.ready', root / 'sender_lifecycle.json'
        env = dict(os.environ, XR_CAPTURE_END_MARKER=str(marker),
                   XR_SENDER_ACCOUNTING=str(accounting))
        child = subprocess.Popen([sys.executable, str(HERE.parent / 'inputs/sender_lifecycle_wrapper.py'),
                                  sys.executable, '-c', CHILD, str(duration), mode], env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (root / 'participant_clock_sender.json').write_text(json.dumps(
            dict(label='sender', pid=child.pid)))
        start = time.monotonic_ns()
        samples = []
        identities = {}
        index = 0
        while time.monotonic_ns() - start < capture_s * 1e9:
            now = time.monotonic_ns()
            samples.append(dict(index=index, monotonic_ns=now,
                                targets=snapshot(root, identities)))
            index += 1
            deadline = start + index * PERIOD_NS
            if time.monotonic_ns() < deadline:
                time.sleep((deadline - time.monotonic_ns()) / 1e9)
        # Extra measured boundary, not a fabricated regular 100 ms sample.
        boundary_ns = time.monotonic_ns()
        samples.append(dict(index=index, monotonic_ns=boundary_ns,
                            boundary=True, targets=snapshot(root, identities)))
        end = samples[-1]['monotonic_ns']
        # The marker is only lifecycle bookkeeping; it does not release source data.
        marker.write_text(str(end))
        stdout, stderr = child.communicate(timeout=4)
        record = json.loads(accounting.read_text()) if accounting.exists() else None
        result = assess(samples, start, end, 'sender', record, HZ)
        return dict(name=name, mode=mode, capture_s=capture_s, exit=child.returncode,
                    periodic_count=len(samples), resource=result,
                    accounting=record, stderr=stderr.decode(), stdout=stdout.decode(),
                    raw_sample_status=[x['targets']['sender']['status'] for x in samples],
                    observed_identities=[[p['identity'] for p in x['targets']['sender']['processes']]
                                         for x in samples])


def main():
    results = [scenario('A_normal', .18),
               scenario('B_during_sampling', .31),
               scenario('C_near_capture_end', .46),
               scenario('D_after_capture_end', .68),
               scenario('E_abnormal_exit', .18, 'abnormal'),
               scenario('F_descendant_waited', .18, 'descendant')]
    baseline = next(x for x in results if x['name'] == 'A_normal')
    base = baseline['resource']
    samples = [dict(index=i, monotonic_ns=i * PERIOD_NS,
                    targets={'sender': {'status': 'OBSERVED', 'root_pid': 1,
                                        'processes': [dict(pid=1, identity=[1, 1],
                                                           utime_ticks=i, stime_ticks=0,
                                                           cutime_ticks=0, cstime_ticks=0,
                                                           rss_bytes=100)]}})
               for i in range(5)]
    fake_accounting = dict(parent_identity=[1, 1], child_identity=[2, 2],
                           child_exit_code=0, wait4_return_ns=150_000_000,
                           child_cpu_user_seconds=.1, child_cpu_system_seconds=0,
                           child_maxrss_kib=123)
    # Add observed child only to first synthetic snapshot, then validate faults.
    samples[0]['targets']['sender']['processes'].append(
        dict(pid=2, identity=[2, 2], utime_ticks=0, stime_ticks=0,
             cutime_ticks=0, cstime_ticks=0, rss_bytes=100))
    changed = json.loads(json.dumps(samples))
    changed[2]['targets']['sender']['processes'][0]['identity'] = [1, 9]
    loss = samples[:2] + samples[3:]
    results += [dict(name='G_identity_change', resource=assess(changed, 0, 400_000_000,
                                                                'sender', fake_accounting, HZ)),
                dict(name='H_periodic_loss', resource=assess(loss, 0, 400_000_000,
                                                              'sender', fake_accounting, HZ)),
                dict(name='I_missing_final_accounting', resource=assess(samples, 0, 400_000_000,
                                                                          'sender', None, HZ))]
    expect = dict(A_normal='PASS', B_during_sampling='PASS',
                  C_near_capture_end='PASS', D_after_capture_end='UNKNOWN',
                  E_abnormal_exit='UNKNOWN', F_descendant_waited='PASS',
                  G_identity_change='UNKNOWN', H_periodic_loss='UNKNOWN',
                  I_missing_final_accounting='UNKNOWN')
    summary = []
    for row in results:
        observed = row['resource']['status']
        expected = expect[row['name']]
        summary.append(dict(case=row['name'], expected=expected,
                            observed=observed, reason=row['resource']['reason'],
                            test_pass=observed == expected))
    output = HERE.parent / 'analysis/lifecycle_preflight.json'
    output.write_text(json.dumps(dict(results=results, summary=summary), indent=2,
                                 sort_keys=True) + '\n')
    for row in summary:
        print(row)
    if not all(row['test_pass'] for row in summary):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
