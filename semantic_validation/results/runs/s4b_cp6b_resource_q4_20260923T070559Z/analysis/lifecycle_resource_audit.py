"""Validate periodic and wait4 evidence without fabricating post-exit samples."""
import json
from pathlib import Path


def cpu_ticks(target):
    # The Q4 sender wrapper has one child. A waited child disappears from /proc
    # at reaping, when its usage becomes parent cutime/cstime. Live descendants
    # are added once. This does not infer individual source-to-command work.
    return sum(p['utime_ticks'] + p['stime_ticks'] + p['cutime_ticks'] +
               p['cstime_ticks'] for p in target['processes'])


def assess(samples, barrier_ns, capture_end_ns, label, accounting, hz, period_ns=100_000_000):
    capture = [r for r in samples if barrier_ns <= r['monotonic_ns'] <= capture_end_ns]
    result = dict(label=label, status='UNKNOWN', cpu_seconds=None, cpu_percent=None,
                  observed_peak_rss_bytes=None, child_final_cpu_seconds=None,
                  child_peak_rss_kib=None, capture_sample_count=len(capture),
                  missing_indices=[], reason=None)
    if len(capture) < 2:
        result['reason'] = 'FEWER_THAN_TWO_CAPTURE_SAMPLES'
        return result
    indices = [r['index'] for r in capture]
    if indices != list(range(indices[0], indices[-1] + 1)):
        result['reason'] = 'PERIODIC_INDEX_LOSS'
        result['missing_indices'] = sorted(set(range(indices[0], indices[-1] + 1)) - set(indices))
        return result
    if any(b['monotonic_ns'] - a['monotonic_ns'] > period_ns * 1.5
           for a, b in zip(capture, capture[1:])):
        result['reason'] = 'PERIODIC_TIME_GAP'
        return result
    targets = [r.get('targets', {}).get(label) for r in capture]
    if any(t is None or t.get('status') != 'OBSERVED' or not t.get('processes') for t in targets):
        result['reason'] = 'RUNNING_OR_LIFECYCLE_ROOT_MISSING'
        return result
    roots = [next((p for p in t['processes'] if p['pid'] == t['root_pid']), None)
             for t in targets]
    if any(p is None for p in roots) or len({tuple(p['identity']) for p in roots}) != 1:
        result['reason'] = 'ROOT_IDENTITY_CHANGED_OR_MISSING'
        return result
    result['observed_peak_rss_bytes'] = max(sum(p['rss_bytes'] for p in t['processes'])
                                            for t in targets)
    if accounting is None:
        result['reason'] = 'NO_FINAL_WAIT4_ACCOUNTING'
        return result
    if tuple(accounting['parent_identity']) != tuple(roots[0]['identity']):
        result['reason'] = 'ACCOUNTING_PARENT_IDENTITY_MISMATCH'
        return result
    child_id = tuple(accounting['child_identity'])
    if not any(child_id == tuple(p['identity']) for t in targets for p in t['processes']):
        result['reason'] = 'CHILD_IDENTITY_NEVER_OBSERVED'
        return result
    if accounting['child_exit_code'] != 0:
        result['reason'] = 'CHILD_ABNORMAL_EXIT'
        return result
    if accounting['wait4_return_ns'] > capture_end_ns:
        result['reason'] = 'CHILD_ACCOUNTED_AFTER_CAPTURE_END'
        # A bounded in-capture counter exists, but full process-lifetime CPU
        # cannot be substituted for the registered capture-window metric.
        return result
    if accounting['wait4_return_ns'] > capture[-1]['monotonic_ns']:
        result['reason'] = 'NO_POST_WAIT4_PERIODIC_SAMPLE_INSIDE_CAPTURE'
        return result
    first_ticks, last_ticks = cpu_ticks(targets[0]), cpu_ticks(targets[-1])
    if last_ticks < first_ticks:
        result['reason'] = 'NON_MONOTONIC_TREE_COUNTER_OR_DOUBLE_COUNT'
        return result
    wall_s = (capture[-1]['monotonic_ns'] - capture[0]['monotonic_ns']) / 1e9
    result.update(status='PASS', reason='OBSERVED_CAPTURE_WITH_FINAL_ACCOUNTING',
                  wall_seconds=wall_s,
                  cpu_seconds=(last_ticks - first_ticks) / hz,
                  cpu_percent=(last_ticks - first_ticks) / hz / wall_s * 100,
                  child_final_cpu_seconds=accounting['child_cpu_user_seconds'] +
                                          accounting['child_cpu_system_seconds'],
                  child_peak_rss_kib=accounting['child_maxrss_kib'])
    return result


def trial(root):
    rows = [json.loads(x) for x in (root / 'resource_samples.jsonl').read_text().splitlines() if x]
    metadata = next(x for x in rows if x.get('kind') == 'resource_metadata')
    samples = [x for x in rows if x.get('kind') == 'sample']
    events = [json.loads(x) for x in (root / 'events.jsonl').read_text().splitlines() if x]
    start = next(x['start_monotonic_ns'] for x in events if x['kind'] == 'barrier_release')
    end_event = next(x['monotonic_ns'] for x in events if x['kind'] == 'capture_end')
    boundary_path = root / 'resource_capture_boundary.json'
    if not boundary_path.exists():
        return dict(status='UNKNOWN', reason='NO_CAPTURE_BOUNDARY')
    boundary = json.loads(boundary_path.read_text())
    span_ns = boundary['acquisition_end_ns'] - boundary['acquisition_start_ns']
    if span_ns < 0 or span_ns > 10_000_000:
        return dict(status='UNKNOWN', reason='BOUNDARY_ACQUISITION_OVER_10MS',
                    acquisition_span_ns=span_ns)
    if boundary['acquisition_end_ns'] > end_event or (
            boundary['boot_id'] != metadata['boot_id'] or
            boundary['time_namespace'] != metadata['time_namespace']):
        return dict(status='UNKNOWN', reason='BOUNDARY_CLOCK_OR_EVENT_ORDER_MISMATCH')
    regular = [x for x in samples if start <= x['monotonic_ns'] <= boundary['acquisition_start_ns']]
    if not regular:
        return dict(status='UNKNOWN', reason='NO_REGULAR_CAPTURE_SAMPLE')
    samples = regular + [dict(kind='boundary', index=regular[-1]['index'] + 1,
                              monotonic_ns=boundary['acquisition_end_ns'],
                              targets=boundary['targets'])]
    path = root / 'sender_lifecycle.json'
    accounting = json.loads(path.read_text()) if path.exists() else None
    result = assess(samples, start, boundary['acquisition_end_ns'], 'sender', accounting,
                    metadata['ticks_per_second'], metadata['period_ns'])
    result['boundary_acquisition_span_ns'] = span_ns
    result['boundary_time_uncertainty_note'] = 'procfs read occurred inside recorded bracket; endpoint timestamp is upper bound'
    if accounting and (accounting['boot_id'] != metadata['boot_id'] or
                       accounting['time_namespace'] != metadata['time_namespace']):
        result.update(status='UNKNOWN', reason='ACCOUNTING_CLOCK_ID_MISMATCH',
                      cpu_seconds=None, cpu_percent=None)
    return result
