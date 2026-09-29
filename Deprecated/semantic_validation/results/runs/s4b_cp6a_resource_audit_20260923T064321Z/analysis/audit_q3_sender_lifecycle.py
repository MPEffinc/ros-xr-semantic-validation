"""Read-only CP6-A audit of immutable Q3 normal-input raw JSONL.

No filesystem mtime is used as an experiment timestamp: Git does not preserve it.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q3 = ROOT.parent / 's4b_cp5b_measurement_20260923T054101Z'


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def audit(trial):
    events = read(trial / 'events.jsonl')
    sent = read(trial / 'sent.jsonl')
    samples = [x for x in read(trial / 'resource_samples.jsonl') if x['kind'] == 'sample']
    topics = read(trial / 'topics.jsonl')
    barrier = next(x['start_monotonic_ns'] for x in events if x['kind'] == 'barrier_release')
    capture_end = next(x['monotonic_ns'] for x in events if x['kind'] == 'capture_end')
    sender_clock = json.loads((trial / 'participant_clock_sender.json').read_text())
    sent_indices = [x['index'] for x in sent]
    assert sent_indices == list(range(120)), (trial.name, sent_indices)
    capture = [x for x in samples if barrier <= x['monotonic_ns'] <= capture_end]
    assert capture, trial.name
    present = [x for x in capture if x['targets'].get('sender', {}).get('status') == 'OBSERVED']
    missing = [x for x in capture if x['targets'].get('sender', {}).get('status') == 'MISSING']
    first_missing = missing[0] if missing else None
    last_present = present[-1] if present else None
    if last_present:
        root = last_present['targets']['sender']
        sender_proc = next((p for p in root['processes'] if p['pid'] == sender_clock['pid']), None)
    else:
        sender_proc = None
    other_missing = {}
    for x in capture:
        for label, target in x['targets'].items():
            if label != 'sender' and target['status'] != 'OBSERVED':
                other_missing[label] = other_missing.get(label, 0) + 1
    indices = [x['index'] for x in capture]
    gaps = [b['monotonic_ns'] - a['monotonic_ns'] for a, b in zip(capture, capture[1:])]
    source_after_missing = ([x['index'] for x in sent if x['send_ns'] >= first_missing['monotonic_ns']]
                            if first_missing else None)
    scheduled_after_missing = ([x['index'] for x in sent
                                if x['scheduled_ns'] >= first_missing['monotonic_ns']]
                               if first_missing else None)
    output_after_missing = None
    if first_missing:
        output_after_missing = {
            topic: sum(x['topic'] == topic and
                       first_missing['monotonic_ns'] <= x['monotonic_ns'] <= capture_end
                       for x in topics)
            for topic in ('/servo_node/delta_twist_cmds',
                          '/joint_group_velocity_controller/commands', '/joint_states')}
    done_exists = (trial / 'sender.done').exists()
    exit_json = json.loads((trial / 'exit.json').read_text())
    missing_followed_by_present = bool(first_missing and any(
        x['monotonic_ns'] > first_missing['monotonic_ns'] for x in present))
    if first_missing and (not done_exists or exit_json['launch_exit'] != 0 or
                          source_after_missing or scheduled_after_missing):
        category = 'UNEXPECTED_PROCESS_EXIT_OR_INCOMPLETE_SOURCE'
    elif first_missing and missing_followed_by_present:
        category = 'RUNNING_SAMPLE_LOSS_OR_TRANSIENT_PROCFS_MISS'
    elif first_missing and last_present and first_missing['monotonic_ns'] > sent[-1]['send_ns']:
        category = 'EXPECTED_PROCESS_EXIT_CONSISTENT_WITH_RAW'
    elif first_missing:
        category = 'UNKNOWN_EXIT_ORDER'
    elif any(g > 150_000_000 for g in gaps) or any(b-a != 1 for a,b in zip(indices, indices[1:])):
        category = 'RUNNING_SAMPLE_LOSS'
    else:
        category = 'NO_MISSING_CAPTURE_SAMPLE'
    return dict(trial=trial.name, classification=category,
                sender_start_ns=sender_clock['monotonic_ns'],
                sender_pid=sender_clock['pid'],
                sender_identity=None if sender_proc is None else sender_proc['identity'],
                last_source_index=sent[-1]['index'],
                last_source_send_start_ns=sent[-1]['send_ns'],
                last_source_scheduled_ns=sent[-1]['scheduled_ns'],
                sender_done_exists=done_exists,
                sender_done_monotonic_ns=None,
                sender_done_time_reason='marker contains no timestamp; filesystem mtime is not versioned raw',
                sender_exit_monotonic_ns=None,
                sender_exit_bound_ns=None if first_missing is None or last_present is None else
                    [last_present['monotonic_ns'], first_missing['monotonic_ns']],
                exit_status=exit_json['launch_exit'],
                capture_start_ns=barrier, capture_end_ns=capture_end,
                capture_sample_count=len(capture),
                max_sample_gap_ms=max(gaps, default=0)/1e6,
                capture_sample_index_gaps=sum(b-a != 1 for a,b in zip(indices,indices[1:])),
                last_present_ns=None if last_present is None else last_present['monotonic_ns'],
                last_present_cpu_seconds=None if sender_proc is None else sender_proc['cpu_time_seconds'],
                last_present_rss_bytes=None if sender_proc is None else sender_proc['rss_bytes'],
                first_missing_ns=None if first_missing is None else first_missing['monotonic_ns'],
                last_present_to_first_missing_ms=None if first_missing is None or last_present is None else
                    (first_missing['monotonic_ns']-last_present['monotonic_ns'])/1e6,
                first_missing_after_last_send_ms=None if first_missing is None else
                    (first_missing['monotonic_ns']-sent[-1]['send_ns'])/1e6,
                first_missing_before_capture_end_ms=None if first_missing is None else
                    (capture_end-first_missing['monotonic_ns'])/1e6,
                source_sent_after_first_missing=source_after_missing,
                source_scheduled_after_first_missing=scheduled_after_missing,
                downstream_records_after_first_missing=output_after_missing,
                other_participant_missing_capture=other_missing,
                no_final_wait4_rusage_in_q3=True)


if __name__ == '__main__':
    roots = sorted((Q3 / 'raw').glob('docker_*setup01'))
    assert len(roots) == 10, len(roots)
    result = [audit(x) for x in roots]
    (ROOT / 'analysis/q3_sender_lifecycle.json').write_text(
        json.dumps(result, indent=2, sort_keys=True) + '\n')
    with (ROOT / 'analysis/q3_sender_lifecycle.csv').open('w', newline='') as stream:
        fields = ('trial', 'classification', 'sender_start_ns', 'last_source_send_start_ns',
                  'sender_done_monotonic_ns', 'sender_exit_monotonic_ns',
                  'last_present_ns', 'first_missing_ns', 'last_present_to_first_missing_ms',
                  'first_missing_after_last_send_ms', 'first_missing_before_capture_end_ms',
                  'capture_end_ns', 'max_sample_gap_ms', 'capture_sample_index_gaps')
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in fields} for row in result)
    for row in result:
        print(row['trial'], row['classification'], row['last_present_to_first_missing_ms'],
              row['source_sent_after_first_missing'])
