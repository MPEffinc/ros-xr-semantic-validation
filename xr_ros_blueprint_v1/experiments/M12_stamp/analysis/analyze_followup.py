#!/usr/bin/env python3
"""R11a follow-up analysis: SRC_STALL_LONG (feeder silent 6.0-11.0 s). Reuses analyze_m12.trial (frozen with R11) for
admission by truth class, and extracts what each available signal showed during the stall:
  A2: validity and OpenVR tracking result carried per command (frame_id fields valid=, res=)
  A3: runtime client flags of the bound client in collector.jsonl (FOCUSED, IO_ACTIVE, INPUTS_BLOCKED)
  both: consecutive identical pose content (descriptive)
  analyze_followup.py <out.json> <dir> ..."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_m12 as M
S0, S1 = 6.0, 11.0
res = []
for d in sys.argv[2:]:
    d = Path(d); r = M.trial(d)
    T = M.A.Trial(d); br = [json.loads(l) for l in open(d / "bridge.jsonl")]
    st = [b for b in br if S0 + 0.1 <= b["t"] <= S1]
    vals = sorted({(kv.split("=")[1]) for b in st for kv in b["frame"].split("|") if kv.startswith("valid=")})
    ress = sorted({(kv.split("=")[1]) for b in st for kv in b["frame"].split("|") if kv.startswith("res=")})
    flags = sorted({(c["focused"], c["io"], c["inputs_blocked"]) for c in T.col if S0 + 0.1 <= c["t"] <= S1})
    same = sum(1 for x, y in zip(st, st[1:]) if x.get("p") == y.get("p"))
    feed = [f for f in T.feed if S0 <= f["t"] <= S1]
    r.update(stall_msgs=len(st), stall_valid_values=vals, stall_tracking_result_values=ress, stall_runtime_flags_focused_io_blocked=flags,
             stall_identical_consecutive=same, feeder_packets_in_stall=len(feed))
    res.append(r)
json.dump(res, open(sys.argv[1], "w"), indent=1, default=str); print(len(res))
