#!/usr/bin/env python3
"""Prospective, non-sending Docker D2/D3 relative source schedule.

This is a case-definition preflight, not a ROS/Gazebo input sender. Source
timestamps and local detection times only exist during an actual runtime.
"""
import argparse
import json
from pathlib import Path


def fixture(case):
    if case not in ('CONTROL', 'D2', 'D3'):
        raise ValueError(case)
    for index in range(120):
        phase = ('idle' if index < 20 else 'reference' if index < 36
                 else 'active' if index < 56 else 'fault_window' if index < 76
                 else 'tail')
        teleop = phase in ('reference', 'active', 'fault_window')
        tracked = not (case == 'D2' and phase == 'fault_window')
        send = not (case == 'D3' and phase == 'fault_window')
        yield dict(index=index, relative_ns=index * 50_000_000,
                   phase=phase, send=send,
                   sample_id=f'docker:{index}' if send else None,
                   generation_id=1 if send else None,
                   source_timestamp='RUNTIME_MONOTONIC_IF_SENT' if send else None,
                   isTracked=tracked if send else None,
                   teleop=teleop if send else None,
                   right_pose=[.35 if phase in ('active', 'fault_window') else .2, .2, .3]
                   if send else None)


def self_test():
    base, d2, d3 = [list(fixture(x)) for x in ('CONTROL', 'D2', 'D3')]
    assert all(len(v) == 120 and [r['index'] for r in v] == list(range(120))
               for v in (base, d2, d3))
    assert [r['index'] for r in d2 if not r['isTracked']] == list(range(56, 76))
    assert [r['index'] for r in d3 if not r['send']] == list(range(56, 76))
    assert sum(r['send'] for r in d2) == 120
    assert sum(r['send'] for r in d3) == 100
    assert all(d2[i]['teleop'] and d2[i]['right_pose'] == base[i]['right_pose']
               and d2[i]['generation_id'] == base[i]['generation_id']
               and d2[i]['relative_ns'] == base[i]['relative_ns'] for i in range(56, 76))
    assert all(d2[i] == base[i] for i in list(range(56)) + list(range(76, 120)))
    assert all(d3[i] == base[i] for i in list(range(56)) + list(range(76, 120)))
    assert d3[55]['isTracked'] and d3[55]['teleop']
    assert d3[55]['relative_ns'] == 2_750_000_000
    assert d3[76]['relative_ns'] == 3_800_000_000
    return {'status': 'PASS_HOST_ONLY', 'control_sent': 120, 'D2_sent': 120,
            'D2_invalid_indices': [56, 75], 'D3_sent': 100,
            'D3_silent_indices': [56, 75],
            'last_D3_real_source_index': 55,
            'first_D3_resumed_source_index': 76,
            'runtime_motion_and_clock': 'UNKNOWN'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    result = self_test()
    for case in ('CONTROL', 'D2', 'D3'):
        with (args.out / f'{case.lower()}_relative_schedule.jsonl').open('w') as stream:
            for row in fixture(case):
                stream.write(json.dumps(row, sort_keys=True) + '\n')
    (args.out / 'host_preflight.json').write_text(json.dumps(result, indent=2,
                                                         sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
