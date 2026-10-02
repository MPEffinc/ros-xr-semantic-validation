"""Frozen F2 case table (PROTOCOL_F2.md §3). Times in s from t0."""
def windows(case):
    if case == 'M1':  return [(t, t + 0.060) for t in (3, 5, 7, 9, 11, 13)]
    if case == 'M2':  return [(t, t + 0.040) for t in (4, 8, 12)]
    if case == 'M4':  return [(2.0 + 0.5 * k, 2.0 + 0.5 * k + (0.005, 0.010, 0.020, 0.040)[k % 4]) for k in range(24)]
    if case in ('M5a', 'M5b'): return [(t, t + 0.200) for t in (4, 8, 12)]
    if case == 'M6b': return [(5.10, 5.20), (9.05, 9.25)]
    return []
def outages(case):
    return [(5.0, 5.3), (9.0, 9.3)] if case in ('M6a', 'M6b') else []
def evidence_delay(case):
    return {'M5a': 0.030, 'M5b': 0.080}.get(case, 0.0)
def deliveries(case, seq, rng):
    """List of delivery delays (s) for command seq; >1 entry = duplicates."""
    if case == 'N1': return [0.010 + rng.uniform(0.0, 0.008)]
    if case == 'M1': return [0.150]
    if case == 'M2': return [0.010, 0.110]
    if case == 'M3': return [0.060 if seq % 2 == 0 else 0.0]
    return [0.010]
CASES = ['N1', 'M1', 'M2', 'M3', 'M4', 'M5a', 'M5b', 'M6a', 'M6b']
