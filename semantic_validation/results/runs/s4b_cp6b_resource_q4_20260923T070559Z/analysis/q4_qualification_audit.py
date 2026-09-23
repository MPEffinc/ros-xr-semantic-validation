"""Frozen before Q4 runtime: classify setup cells, never defense performance."""
import csv
import importlib.util
import json
from pathlib import Path

from q4_measurement_audit import audit as measure, rows
from q3_stop_audit import audit as stop_audit

ROOT = Path(__file__).resolve().parents[1]
PAIR_PATH = ROOT.parent / 's4b_cp2_qualification_20260923T003626Z/analysis/pair_audit.py'
spec = importlib.util.spec_from_file_location('fixed_pair_audit', PAIR_PATH)
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)
pair.ROOT = ROOT
pair.RAW = ROOT / 'raw'


def inspect_cell(cell):
    name = '_'.join(('docker', 'b2c' if cell['baseline'] == 'b2c' else cell['baseline'],
                     cell['regime'], cell['attempt_id']))
    root = ROOT / 'raw' / name
    if not root.exists():
        return dict(cell=cell['cell'], trial=name, status='NOT_RUN', reasons=['NO_RAW'])
    reasons = []
    if not (root / 'exit.json').exists():
        return dict(cell=cell['cell'], trial=name, status='UNKNOWN', reasons=['NO_LAUNCH_EXIT'])
    exit_code = json.loads((root / 'exit.json').read_text()).get('launch_exit')
    if exit_code != 0:
        reasons.append(f'LAUNCH_EXIT_{exit_code}')
    sent = rows(root / 'sent.jsonl')
    if [x.get('index') for x in sent] != list(range(120)):
        reasons.append('NOT_120_ORDERED_SOURCE_INDICES')
    events = rows(root / 'events.jsonl')
    ack = next((x for x in events if x.get('kind') == 'readiness_ack'), None)
    barrier = next((x.get('start_monotonic_ns') for x in events
                    if x.get('kind') == 'barrier_release'), None)
    if not ack or barrier is None:
        reasons.append('NO_FULL_START_ACK_OR_BARRIER')
    clock_rows = [x for x in rows(root / 'resource_samples.jsonl')
                  if x.get('kind') == 'resource_metadata']
    if not clock_rows or not ack or len({x.get('boot_id') for x in ack.get('participant_clocks', {}).values()}) != 1:
        reasons.append('CLOCK_CONTRACT_UNVERIFIED')
    if reasons:
        return dict(cell=cell['cell'], trial=name, status='BLOCKED_OR_UNKNOWN',
                    reasons=reasons, exit_code=exit_code, source_count=len(sent))
    measurement = measure(root)
    resource = measurement['resources']
    if resource['status'] != 'COMPLETE_CAPTURE':
        reasons.append('PERIODIC_RESOURCE_CAPTURE_INCOMPLETE')
    sender = resource['q4_sender_lifecycle']
    if sender['status'] != 'PASS':
        reasons.append('SENDER_' + sender['reason'])
    if cell['diagnostic'] == 'normal':
        motion = pair.trial(name, 120) if not reasons else None
        if motion and not (motion['active_controller_output_records'] > 0 and
                           motion['max_joint_excursion_rad'] > .01):
            reasons.append('NO_CONTROLLER_OR_GAZEBO_POSITIVE_CONTROL')
        if cell['baseline'] != 'b0':
            callback = measurement['callback']
            if (callback['source_parent_publications'] == 0 or
                    callback['exact_joins'] != callback['source_parent_publications'] or
                    callback['missing']):
                reasons.append('SOURCE_TO_SERVO_CALLBACK_JOIN_INCOMPLETE')
        if cell['baseline'] == 'b2':
            if cell['regime'] == 'full':
                m = measurement['monitor']
                if not m or m['exact_full_transport_joins'] != m['property_records']:
                    reasons.append('B2_FULL_ORACLE_TRANSPORT_JOIN_INCOMPLETE')
            else:
                m = measurement.get('native_b2_exact_binding', {})
                if m.get('source_bound_joins') != 372 or m.get('ambiguous'):
                    reasons.append('B2_NATIVE_ACTIVE_SOURCE_PROPERTY_JOIN_INCOMPLETE')
    else:
        stop = stop_audit(root)
        if stop['status'] != 'PASS_STOP_SETUP':
            reasons.append('ORDINARY_STOP_NOT_QUALIFIED')
    return dict(cell=cell['cell'], trial=name,
                status='QUALIFIED_SETUP' if not reasons else 'BLOCKED_OR_UNKNOWN',
                reasons=reasons, exit_code=exit_code, source_count=len(sent),
                sender_resource=sender,
                max_joint_excursion_rad=None if cell['diagnostic'] != 'normal' or not motion
                else motion['max_joint_excursion_rad'],
                stop=None if cell['diagnostic'] != 'stop' else stop)


def main():
    with (ROOT / 'qualification_schedule.csv').open() as file:
        schedule = list(csv.DictReader(file))
    assert len(schedule) == 16 and [x['order'] for x in schedule] == [str(i) for i in range(1, 17)]
    results = [inspect_cell(cell) for cell in schedule]
    b0 = ROOT / 'raw/docker_b0_full_q4b0setup01'
    shim = ROOT / 'raw/docker_shim_full_q4shimsetup01'
    equivalence = pair.summarize(b0.name, shim.name, 120) if b0.exists() and shim.exists() else None
    all_ready = all(x['status'] == 'QUALIFIED_SETUP' for x in results) and \
        equivalence is not None and equivalence['status'] == 'PASS'
    output = dict(status='D1_QUALIFICATION_PASS' if all_ready else 'D1_FORMAL_BLOCKED',
                  setup_cells=results, b0_shim_equivalence=equivalence,
                  formal_trials='NOT_STARTED',
                  specific_source_to_controller_joint_parent='UNKNOWN_INTERVAL_ONLY')
    (ROOT / 'analysis/q4_qualification_summary.json').write_text(json.dumps(
        output, indent=2, sort_keys=True) + '\n')
    for row in results:
        print(row['cell'], row['status'], row['reasons'])
    print('D1', output['status'])


if __name__ == '__main__':
    main()
