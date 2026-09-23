"""Read-only Q3 latency/resource audit with exact IDs and bounded output claims."""
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def rows(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def source_origin(parent):
    while isinstance(parent, dict):
        if 'sample_id' in parent:
            return parent
        parent = parent.get('parent')
    return None


def pub_key(record):
    payload = record['payload']
    header = payload['header']
    twist = payload['twist']
    return (header['stamp']['sec'], header['stamp']['nanosec'], header['frame_id'],
            *(twist['linear'][axis] for axis in 'xyz'),
            *(twist['angular'][axis] for axis in 'xyz'))


def callback_key(record):
    return (record['stamp_sec'], record['stamp_nanosec'], record['frame_id'],
            *record['linear'], *record['angular'])


def distribution(values):
    if not values:
        return None
    values = sorted(values)
    p95 = values[max(0, int((len(values) * .95 + .999999999) - 1))]
    return dict(count=len(values), min=min(values), median=statistics.median(values),
                p95=p95, max=max(values))


def callback_latency(root):
    sent = {f'docker:{row["index"]}': row for row in rows(root / 'sent.jsonl')}
    pubs = [row for row in rows(root / 'lineage.jsonl')
            if row.get('kind') == 'publish' and row.get('stage') == 'bridge_servo_input']
    cb_by_key = defaultdict(list)
    for row in rows(root / 'servo_callback_payload.jsonl'):
        cb_by_key[callback_key(row)].append(row)
    pub_counts = Counter(pub_key(row) for row in pubs)
    source_pubs = [row for row in pubs if source_origin(row.get('parent'))]
    joined = []
    missing = []
    for row in source_pubs:
        origin = source_origin(row['parent'])
        sample_id = origin['sample_id']
        candidates = cb_by_key[pub_key(row)]
        if pub_counts[pub_key(row)] != 1 or len(candidates) != 1 or sample_id not in sent:
            missing.append(dict(sample_id=sample_id, command_id=row['command_id'],
                                reason='NON_UNIQUE_OR_MISSING_EXACT_PAYLOAD_OR_SOURCE'))
            continue
        cb = candidates[0]
        source_ns = sent[sample_id]['sample_ns']
        if source_ns != origin['source_timestamp_ns']:
            missing.append(dict(sample_id=sample_id, command_id=row['command_id'],
                                reason='SOURCE_TIME_MISMATCH'))
            continue
        joined.append(dict(sample_id=sample_id, generation_id=origin['generation_id'],
                           command_id=row['command_id'], phase=origin['phase'],
                           source_ns=source_ns, publish_ns=row['monotonic_ns'],
                           callback_entry_ns=cb['entry_ns'],
                           sample_to_callback_ms=(cb['entry_ns'] - source_ns) / 1e6,
                           publish_to_callback_ms=(cb['entry_ns'] - row['monotonic_ns']) / 1e6))
    active = [x['sample_to_callback_ms'] for x in joined if x['phase'] == 'active']
    return dict(source_parent_publications=len(source_pubs), exact_joins=len(joined),
                missing=missing, active_source_to_servo_callback_ms=distribution(active),
                all_source_to_servo_callback_ms=distribution(
                    [x['sample_to_callback_ms'] for x in joined]),
                joined=joined)


def monitor_latency(root):
    lineage = rows(root / 'lineage.jsonl')
    sent_events = {x.get('monitor_event_id'): x for x in lineage
                   if x.get('stage') == 'receiver_envelope' and x.get('monitor_event_id') is not None}
    received = {x.get('monitor_event_id'): x for x in lineage
                if x.get('kind') == 'monitor_output_received' and x.get('regime') == 'full'}
    property_rows = rows(root / 'property.jsonl')
    complete = []
    missing = 0
    for item in property_rows:
        event_id = item.get('monitor_event_id')
        if event_id not in sent_events or event_id not in received:
            missing += 1
            continue
        t_input = sent_events[event_id]['monotonic_ns']
        t_decision = item['monotonic_ns']
        t_received = received[event_id]['monotonic_ns']
        complete.append(dict(event_id=event_id, sample_id=item.get('sample_id'),
                             phase=sent_events[event_id].get('selected_origin', {}).get('phase'),
                             decision_after_publish_ms=(t_decision - t_input) / 1e6,
                             output_received_after_decision_ms=(t_received - t_decision) / 1e6))
    active = [x for x in complete if x['phase'] == 'active']
    return dict(property_records=len(property_rows), exact_full_transport_joins=len(complete),
                unjoined_records=missing,
                active_decision_after_input_ms=distribution([x['decision_after_publish_ms'] for x in active]),
                active_output_received_after_decision_ms=distribution(
                    [x['output_received_after_decision_ms'] for x in active]),
                internal_monitor_forward_time='UNKNOWN', joined=complete)


def resources(root):
    data = rows(root / 'resource_samples.jsonl')
    samples = [x for x in data if x.get('kind') == 'sample']
    if not samples:
        return dict(status='UNKNOWN', reason='NO_100MS_SAMPLES')
    events = rows(root / 'events.jsonl')
    barrier = next((x['start_monotonic_ns'] for x in events if x.get('kind') == 'barrier_release'), None)
    end = next((x['monotonic_ns'] for x in events if x.get('kind') == 'capture_end'), None)
    ack = next((x for x in events if x.get('kind') == 'readiness_ack'), None)
    expected_labels = sorted((ack or {}).get('participant_clocks', {}))
    capture = [x for x in samples if barrier is not None and end is not None and barrier <= x['monotonic_ns'] <= end]
    intervals = [(b['monotonic_ns'] - a['monotonic_ns']) / 1e6
                 for a, b in zip(samples, samples[1:])]
    labels = sorted({label for row in samples for label in row['targets']})
    absent_labels = sorted(set(expected_labels) - set(labels))
    missing = {label: sum(row['targets'].get(label, {}).get('status') != 'OBSERVED'
                          for row in samples) for label in labels}
    per_label = {}
    if len(capture) >= 2:
        wall_s = (capture[-1]['monotonic_ns'] - capture[0]['monotonic_ns']) / 1e9
        for label in labels:
            per_pid = defaultdict(list)
            rss = []
            missing_capture = 0
            for row in capture:
                target = row['targets'].get(label)
                if target is None or target['status'] != 'OBSERVED':
                    missing_capture += 1
                    continue
                rss.append(sum(proc['rss_bytes'] for proc in target['processes']))
                for proc in target['processes']:
                    per_pid[tuple(proc['identity'])].append((row['monotonic_ns'], proc['cpu_time_seconds']))
            cpu_s = sum(max(0, values[-1][1] - values[0][1]) for values in per_pid.values() if len(values) >= 2)
            partial = sum(len(values) < 2 or values[0][0] > capture[0]['monotonic_ns'] or values[-1][0] < capture[-1]['monotonic_ns'] for values in per_pid.values())
            per_label[label] = dict(cpu_seconds=cpu_s,
                                    cpu_percent=(cpu_s / wall_s * 100) if wall_s > 0 and not missing_capture else None,
                                    max_tree_rss_bytes=max(rss) if rss else None,
                                    missing_capture_samples=missing_capture,
                                    partial_lifetime_processes=partial,
                                    process_identities=len(per_pid))
    valid_capture = len(capture) >= 2 and not absent_labels and not any(
        any(row['targets'].get(label, {}).get('status') != 'OBSERVED'
            for row in capture) for label in expected_labels)
    return dict(status='COMPLETE_CAPTURE' if valid_capture else 'UNKNOWN_INCOMPLETE_CAPTURE',
                expected_labels=expected_labels, absent_labels=absent_labels,
                sample_count=len(samples),
                interval_ms=distribution(intervals), labels=labels, missing_by_label=missing,
                capture_sample_count=len(capture), per_label=per_label,
                cpu_rss_records='resource_samples.jsonl; CPU and RSS are raw per-PID/start-tick records')


def audit(root):
    return dict(trial=root.name, callback=callback_latency(root),
                monitor=monitor_latency(root) if (root / 'monitor_full_status.jsonl').exists() else None,
                resources=resources(root),
                servo_to_specific_controller_parent='UNKNOWN',
                specific_source_to_joint_parent='UNKNOWN')


if __name__ == '__main__':
    import sys
    root = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.write_text(json.dumps(audit(root), indent=2, sort_keys=True) + '\n')
