from pathlib import Path
import csv
import json

project = Path(__file__).resolve().parents[1]
db = json.loads((project / "data/blueprint.json").read_text())
tables = db["tables"]
for name, rows in tables.items():
    ids = [r["id"] for r in rows if "id" in r]
    assert len(ids) == len(set(ids)), f"duplicate IDs: {name}"
ids = {name: {r["id"] for r in rows if "id" in r} for name, rows in tables.items()}
for row in tables["cases"]:
    for field, table in [("taxonomy_ids", "taxonomy"), ("flow_ids", "flows"), ("baselines", "defenses"), ("source_ids", "sources"), ("limitation_ids", "limitations")]:
        values = [s.strip() for s in row.get(field, "").split(",") if s.strip()]
        assert set(values) <= ids[table], (row["id"], field, set(values) - ids[table])
for row in tables["matrix"]:
    for field, table in [("case_id", "cases"), ("defense_id", "defenses")]:
        assert row[field] in ids[table], (row["id"], field)
view = project / "data/csv"
view.mkdir(exist_ok=True)
for name, rows in tables.items():
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (view / (name + ".csv")).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
print("ID links valid; CSV views regenerated", {k: len(v) for k, v in tables.items()})
