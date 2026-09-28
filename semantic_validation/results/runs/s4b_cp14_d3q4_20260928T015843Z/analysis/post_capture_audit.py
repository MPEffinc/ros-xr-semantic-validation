"""Exact prospective Q3 producer-quiesce and monitor-drain audit."""
import json


def rows(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def audit(root, mode):
    if mode == 'b0':
        return dict(status='NOT_APPLICABLE_ORIGINAL_B0', issues=[])
    events = rows(root / 'events.jsonl')
    lineage = rows(root / 'lineage.jsonl')
    capture = [r for r in events if r.get('kind') == 'capture_end']
    quiesced = [r for r in lineage if r.get('kind') == 'post_capture_receiver_quiesced']
    ack = [r for r in events if r.get('kind') == 'post_capture_receiver_quiesce_ack']
    issues = []
    if len(capture) != 1 or len(quiesced) != 1 or len(ack) != 1 or not (root / 'receiver_quiesced.ready').exists():
        issues.append('MISSING_EXACT_CAPTURE_QUIESCE_ACK')
    else:
        if quiesced[0]['monotonic_ns'] < capture[0]['monotonic_ns']:
            issues.append('PRODUCER_QUIESCED_BEFORE_OUTCOME_CAPTURE_END')
        if ack[0].get('quiesce_ns') != quiesced[0]['monotonic_ns']:
            issues.append('QUIESCE_ACK_TIME_MISMATCH')
        publications = [r for r in lineage if r.get('kind') == 'publish' and
                        r.get('stage') in ('receiver', 'receiver_envelope',
                                           'receiver_native_monitor_input')]
        if any(r['monotonic_ns'] > quiesced[0]['monotonic_ns'] for r in publications):
            issues.append('ORIGINAL_PUBLICATION_AFTER_QUIESCE')
    if mode == 'b2':
        drains = [r for r in events if r.get('kind') == 'post_capture_monitor_drain_ack']
        if (len(drains) != 1 or drains[0].get('result', {}).get('status') != 'PASS'
                or drains[0].get('tick_property_count') != 300
                or drains[0].get('tick_status_count') != 300):
            issues.append('EXACT_OFFICIAL_MONITOR_DRAIN_ACK_MISSING')
    return dict(status='PASS' if not issues else 'BLOCKED_MEASUREMENT',
                issues=issues, capture_end_ns=capture[0]['monotonic_ns'] if capture else None,
                quiesce_ns=quiesced[0]['monotonic_ns'] if quiesced else None,
                original_publications_after_quiesce=0 if not issues else 'SEE_ISSUES',
                exact_monitor_drain_ack=(mode == 'b2' and not issues))
