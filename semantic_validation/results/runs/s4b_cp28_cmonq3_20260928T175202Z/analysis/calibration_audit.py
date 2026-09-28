"""Q4 calibration is separate from sender samples, original neutrals and ticks."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'inputs'))
from source_path_readiness import canonical_hash, exact_ack, read_rows


def audit(root, regime):
    root = Path(root)
    issues = []
    attempts, malformed = read_rows(root / 'calibration.jsonl')
    if malformed:
        return dict(status='BLOCKED_MEASUREMENT', issues=[malformed])
    verdicts, malformed = read_rows(root / 'calibration_verdicts.jsonl')
    if malformed:
        issues.append(malformed)
    events, malformed = read_rows(root / 'events.jsonl')
    if malformed:
        issues.append(malformed)
    lineage, malformed = read_rows(root / 'lineage.jsonl')
    if malformed:
        issues.append(malformed)
    if not (1 <= len(attempts) <= 12) or [r.get('attempt') for r in attempts] != list(range(1, len(attempts)+1)):
        issues.append('CALIBRATION_ATTEMPT_SEQUENCE')
    keys = [r.get('key') for r in attempts]
    if len(keys) != len(set(keys)):
        issues.append('DUPLICATE_CALIBRATION_ID')
    if len(verdicts) != len(attempts):
        issues.append('CALIBRATION_ATTEMPT_VERDICT_COVERAGE')
    if any(r.get('source_sample') is not False or r.get('control_input') is not False or
           r.get('native_payload', {}).get('tracked') is not False or
           r.get('native_payload', {}).get('teleop_enable') is not False or
           r.get('native_payload', {}).get('source') != 'readiness_calibration'
           for r in attempts):
        issues.append('CALIBRATION_NOT_NEUTRAL_NON_SOURCE')
    if regime == 'native' and any(canonical_hash(r['native_payload']) != r['key'] for r in attempts):
        issues.append('NATIVE_CALIBRATION_PAYLOAD_HASH')
    marker = root / 'source_path_calibration.ready'
    try:
        selected = json.loads(marker.read_text())
    except (OSError, json.JSONDecodeError):
        selected = None
        issues.append('EXACT_CALIBRATION_MARKER_MISSING')
    ack = [r for r in lineage if r.get('kind') == 'source_path_calibration_ack']
    release = [r for r in lineage if r.get('kind') == 'receiver_timer_release']
    barrier = [r for r in events if r.get('kind') == 'barrier_release']
    readiness = [r for r in events if r.get('kind') == 'readiness_ack']
    dds = [r for r in lineage if r.get('kind') == 'pre_spin_monitor_dds_match']
    if not (len(ack) == len(release) == len(barrier) == len(readiness) == len(dds) == 1):
        issues.append('CALIBRATION_CLOCK_CHAIN_RECORDS_INCOMPLETE')
    matched = next((r for r in attempts if selected and r.get('attempt') == selected.get('attempt')
                    and r.get('key') == selected.get('key')), None)
    current = exact_ack(root, regime, matched) if matched else {'ok': False, 'reason': 'NO_SELECTED_ATTEMPT'}
    if not current['ok']:
        issues.append('SELECTED_CALIBRATION_NOT_EXACTLY_RECEIVED')
    if matched and len(ack) == len(release) == len(barrier) == len(readiness) == len(dds) == 1:
        timing = [dds[0]['dds_match_monotonic_ns'], matched['created_monotonic_ns'],
                  current.get('oracle_decision_monotonic_ns', 0),
                  current.get('guarded_receipt_monotonic_ns', 0),
                  selected['ack_monotonic_ns'], release[0]['monotonic_ns'],
                  barrier[0]['monotonic_ns']]
        if any(a > b for a, b in zip(timing, timing[1:])):
            issues.append('CALIBRATION_CLOCK_ORDER_INVALID')
        if readiness[0].get('source_path_calibration', {}).get('key') != matched['key']:
            issues.append('COMMON_START_ACK_LACKS_EXACT_CALIBRATION')
        if any(r['monotonic_ns'] <= release[0]['monotonic_ns']
               for r in lineage if r.get('stage') in ('receiver_envelope', 'receiver_native_monitor_input')):
            issues.append('ORIGINAL_TIMER_PUBLISHED_BEFORE_RELEASE')
    else:
        timing = None
    source_records, _ = read_rows(root / 'sent.jsonl')
    ticks, _ = read_rows(root / 'd3_ticks.jsonl')
    if any(r.get('key') in {row.get('sample_id') for row in source_records} for r in attempts):
        issues.append('CALIBRATION_MIXED_WITH_SENDER')
    if any(r.get('source_sample_id') is not None for r in ticks):
        issues.append('TICK_FABRICATED_SOURCE')
    mapper_calibration = [r for r in lineage
                          if r.get('kind') == 'mapper_applied_after_original_callback'
                          and (r.get('exact_parent') or {}).get('parent', {}).get('reason') == 'readiness_calibration']
    if not mapper_calibration:
        issues.append('CALIBRATION_NOT_OBSERVED_AT_ORIGINAL_MAPPER')
    if any(r.get('state', {}).get(field) is not False
           for r in mapper_calibration
           for field in ('teleop_enabled', 'position_session_active', 'position_recenter_pending')):
        issues.append('CALIBRATION_ALTERED_REFERENCE_OR_CONTROL_STATE')
    if len(barrier) == 1:
        topics, malformed = read_rows(root / 'topics.jsonl')
        if malformed:
            issues.append(malformed)
        early = [r for r in topics if r.get('topic') == '/joint_group_velocity_controller/commands'
                 and r['monotonic_ns'] < barrier[0]['monotonic_ns']]
        if any(any(abs(float(v)) > 1e-6 for v in r.get('payload', {}).get('data', [])) for r in early):
            issues.append('PRE_BARRIER_NONZERO_CONTROLLER_COMMAND')
    return dict(status='PASS' if not issues else 'BLOCKED_MEASUREMENT', issues=issues,
                calibration_attempts=len(attempts), all_attempts=attempts,
                all_verdicts=verdicts, selected_attempt=matched,
                selected_exact_path=current, monotonic_chain=timing,
                official_status_monotonic_ns='UNKNOWN_WITHOUT_VALIDATED_WALL_MAPPING',
                original_source_events_excluded=0,
                mapper_calibration_receipts=len(mapper_calibration))
