#!/usr/bin/env python3
"""M12_watchdog analysis (R15). Truth classes, admission and false blocks from the frozen R11 analyze_m12.trial()
(truth: stale_source iff no feeder packet within 100 ms before the bridge received the app message). Added:
  stall_start/stall_end, last admitted command after stall start, first admitted command after stall end
  (recovery latency), the target jump between the last admitted command before the stall and the first after it,
  and app message count inside the stall (the watchdog makes the app go silent).
  analyze_wd.py trial <dir> <cond>   |   analyze_wd.py set <out.json> <schedule.csv> <raw_dir>"""
import csv, json, math, sys
from pathlib import Path
sys.path.insert(0, "/m12/analysis") if Path("/m12/analysis").exists() else None
import analyze_m12 as M
CMAP = {"N_MOVE": "N_MOVE", "N_STILL": "N_STILL", "STALL15": "SRC_STALL", "STALL5": "SRC_STALL_LONG"}
STALL = {"STALL15": (6.0, 7.5), "STALL5": (6.0, 11.0)}
def trial(d, cond):
    d = Path(d); r = M.trial(d, None, CMAP[cond]); r["cond"] = cond
    if r.get("invalid"): return r
    g = [json.loads(l) for l in open(d / "gate.jsonl")]; br = [json.loads(l) for l in open(d / "bridge.jsonl")]
    if cond in STALL:
        s0, s1 = STALL[cond]
        adm = [x for x in g if x["admit"]]
        before = [x for x in adm if x["t"] < s0]; after = [x for x in adm if x["t"] > s0]
        last_after_start = max((x["t"] for x in adm if s0 <= x["t"] <= s1), default=None)
        first_after_end = next((x for x in adm if x["t"] >= s1), None)
        r.update(stall=[s0, s1], app_msgs_in_stall=sum(1 for b in br if s0 + 0.1 <= b["t"] <= s1),
                 admitted_in_stall=sum(1 for x in adm if s0 + 0.1 <= x["t"] <= s1),
                 last_admit_after_stall_start_s=None if last_after_start is None else round(last_after_start - s0, 3),
                 recovery_first_admit_after_end_s=None if first_after_end is None else round(first_after_end["t"] - s1, 3))
        if before and first_after_end is not None:
            pb, pa = before[-1]["p"], first_after_end["p"]
            r["resume_target_jump_mm"] = round(math.dist(pb, pa) * 1000, 2)
    return r
if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(trial(sys.argv[2], sys.argv[3]), indent=1, default=str))
    else:
        out, sched, raw = sys.argv[2], sys.argv[3], Path(sys.argv[4]); res = []
        for row in csv.DictReader(open(sched)):
            for d in sorted(raw.glob(row["trial_id"] + "*")): x = trial(d, row["cond"]); x["arm"] = row["arm"]; res.append(x)
        json.dump(res, open(out, "w"), indent=1, default=str); print(len(res))
