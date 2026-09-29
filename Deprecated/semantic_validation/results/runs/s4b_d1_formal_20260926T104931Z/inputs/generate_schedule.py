"""Generate the XRROS-S4-1.0.0 Docker D1 five-repeat schedule once, before runtime."""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMS = [
    ('b0', 'full', '0'), ('shim', 'full', '0'),
    ('b1', 'native', '0'), ('b1', 'full', '0'),
    ('b2', 'native', '0'), ('b2', 'full', '0'),
    ('b2', 'native', '1'), ('b2', 'full', '1'),
    ('b3', 'native', '0'), ('b3', 'full', '0'),
]
SEED = 20260922


def generate():
    rng = random.Random(SEED)
    rows = []
    for repetition in range(1, 6):
        arms = ARMS.copy()
        rng.shuffle(arms)
        for mode, regime, composed in arms:
            variant = 'b2c' if composed == '1' else mode
            trial_id = f'docker_d1_r{repetition:02d}_{variant}_{regime}'
            rows.append(dict(order=len(rows) + 1, case='D1', repetition=repetition,
                             mode=mode, regime=regime, composed=composed,
                             trial_id=trial_id, seed=SEED))
    assert len(rows) == 50 and len({x['trial_id'] for x in rows}) == 50
    return rows


if __name__ == '__main__':
    target = ROOT / 'schedule.csv'
    with target.open('x', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(generate()[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(generate())
