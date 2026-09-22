"""Offline read-only raw analysis; receipt monotonic time is NOT source causality."""
import collections,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NAMES=['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint']
def read(path):
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
results={}
for trial in sorted((ROOT/'raw').iterdir()):
    if not trial.is_dir(): continue
    events=read(trial/'events.jsonl'); topics=read(trial/'topics.jsonl'); lineage=read(trial/'lineage.jsonl')
    joints=[]
    for row in topics:
        if row['topic']!='/joint_states':continue
        p=row['payload']
        try:
            idx=[p['name'].index(n) for n in NAMES]
            joints.append((row['monotonic_ns'],[p['position'][i] for i in idx],[p['velocity'][i] for i in idx]))
        except (ValueError,IndexError):pass
    phases={}
    for event in events:
        if event['kind']!='phase_start':continue
        end=next((x['monotonic_ns'] for x in events if x['kind']=='phase_end' and x['name']==event['name'] and x['monotonic_ns']>event['monotonic_ns']),None)
        if end is None:continue
        selected=[s for s in joints if event['monotonic_ns']<=s[0]<end]
        def metrics(ss):
            return {'samples':len(ss),'max_excursion_rad':max(max(s[1][i] for s in ss)-min(s[1][i] for s in ss) for i in range(6)),
              'max_velocity_rad_s':max(abs(v) for s in ss for v in s[2])} if ss else {'samples':0}
        phases[event['name']]={'input':event,'start_ns':event['monotonic_ns'],'end_ns':end,
           'joints':metrics(selected),'last_half_second':metrics([s for s in selected if s[0]>=end-500_000_000]),
           'topic_counts':dict(collections.Counter(r['topic'] for r in topics if event['monotonic_ns']<=r['monotonic_ns']<end))}
    pubs=[x for x in lineage if x['kind']=='publish']; consumes=[x for x in lineage if x['kind']=='consume']
    results[trial.name]={'events':events,'phases':phases,'final_joint_position':joints[-1][1] if joints else None,
       'lineage_publish_counts':dict(collections.Counter(x['stage'] for x in pubs)),
       'lineage_consume_associations':dict(collections.Counter(x['association'] for x in consumes)),
       'source_parent_null':sum(x.get('parent') is None for x in pubs),
       'exit':read(trial/'exit.json') if False else json.loads((trial/'exit.json').read_text()) if (trial/'exit.json').exists() else None}
print(json.dumps(results,indent=2,sort_keys=True))
