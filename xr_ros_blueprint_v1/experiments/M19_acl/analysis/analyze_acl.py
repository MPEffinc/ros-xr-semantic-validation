#!/usr/bin/env python3
"""M19 analysis (R27). Per trial:
  enforced      : the no-enclave probe node was NOT created under Enforce (else invalid: security_not_enforced)
  key_access    : what uid 2001 (app) could read
  publisher     : create_publisher ok/failed, matched subscriber count, publish ok (API level; not used as delivery evidence)
  on_ctl_topic  : the observer (permitted reader) received the payload on the controller topic
  ctl_reference : the JTC controller_state reference reached the payload (controller accepted it)
  joints_moved  : /joint_states shoulder_pan within 0.01 rad of the payload (mock hardware executed it)
  reached_controller = ctl_reference or joints_moved
Invalid: setup failure, missing observer joint states (controller not running), security not enforced.
  analyze_acl.py trial <dir> <deploy> <check> | set <out.json> <schedule.csv> <raw_dir>"""
import csv, json, sys
from pathlib import Path
Q0 = [-2.865212, -0.02629, -1.853711, -1.261592, -2.865212, -1.571593]; TGT = Q0[0] + 0.20
def jl(p): return [json.loads(l) for l in open(p) if l.strip()] if Path(p).exists() else []
def trial(d, deploy, check):
    d = Path(d); H = jl(d / "harness.jsonl"); O = jl(d / "observer.jsonl"); P = jl(d / "pub.jsonl"); S = (jl(d / "setup.json") or [{}])[0]
    out = {"trial": d.name, "deploy": deploy, "check": check, "invalid": []}
    pe = next((h for h in H if h["ev"] == "probe_enforce"), None); enforced = pe is not None and not pe["node_created"]
    js = [o for o in O if o["k"] == "js"]
    if S.get("setup") != "ok": out["invalid"].append("setup")
    if not js: out["invalid"].append("no_joint_states")
    if not enforced: out["invalid"].append("security_not_enforced")
    def pan(o): return dict(zip(o["names"], o["pos"])).get("shoulder_pan_joint")
    t_pay = next((h["wall"] for h in H if h["ev"] == "payload_start"), None)
    on_ctl = any(o["k"] == "ctl_topic" and o["pos"] and abs(o["pos"][0] - TGT) < 1e-6 for o in O)
    on_app = any(o["k"] == "app_topic" and o["pos"] and abs(o["pos"][0] - TGT) < 1e-6 for o in O)
    ref = any(o["k"] == "ref" and o["pos"] and abs(pan(o) - TGT) < 1e-3 for o in O)
    moved = any(abs(pan(o) - TGT) < 0.01 for o in js if pan(o) is not None)
    pre = [pan(o) for o in js if t_pay and o["wall"] < t_pay and pan(o) is not None]
    out.update(enforced=enforced, probe_rc=pe and pe["rc"], key_access={h["file"]: h["result"] for h in H if h["ev"] == "key_access"},
               app_permissions_sha16=next((h["sha16"] for h in H if h["ev"] == "app_permissions"), None),
               publisher=[{k: v for k, v in p.items() if k in ("k", "topic", "matched", "sent", "err")} for p in P],
               on_app_topic=on_app, on_ctl_topic=on_ctl, ctl_reference=ref, joints_moved=moved, reached_controller=ref or moved,
               pan_before=round(pre[-1], 4) if pre else None, pan_final=round(pan(js[-1]), 4) if js else None)
    return out
if __name__ == "__main__":
    if sys.argv[1] == "trial": print(json.dumps(trial(*sys.argv[2:5]), indent=1))
    else:
        out, sched, raw = sys.argv[2], sys.argv[3], Path(sys.argv[4]); res = []
        for row in csv.DictReader(open(sched)):
            for d in sorted(raw.glob(row["trial_id"] + "*")): res.append(trial(d, row["deploy"], row["check"]))
        json.dump(res, open(out, "w"), indent=1); print(len(res))
