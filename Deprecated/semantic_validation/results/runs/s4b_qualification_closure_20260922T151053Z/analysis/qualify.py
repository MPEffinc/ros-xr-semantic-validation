"""Recompute qualification from recorded topic callbacks, source and service events."""
import json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NAMES=['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint']
def lines(path):return [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
def tip(parent):
    while isinstance(parent,dict):
        if 'sample_id' in parent:return parent['sample_id']
        parent=parent.get('parent') or parent.get('exact_parent')
    return None
def settled(joints,trigger):
    for end,pos,vel in joints:
        if end<trigger+500_000_000 or end>trigger+1_000_000_000:continue
        w=[x for x in joints if end-500_000_000<=x[0]<=end]
        if len(w)<3 or w[-1][0]-w[0][0]<450_000_000:continue
        drift=max(max(x[1][i] for x in w)-min(x[1][i] for x in w) for i in range(6))
        speed=max(abs(v) for x in w for v in x[2])
        if drift<.0001 and speed<.001:return {'from_trigger_ms':(end-trigger)/1e6,'max_window_drift_rad':drift,'max_window_speed_rad_s':speed}
    return None
results={}
for trial in sorted((ROOT/'raw').iterdir()):
    if not trial.is_dir():continue
    ev=lines(trial/'events.jsonl'); ts=lines(trial/'topics.jsonl'); lin=lines(trial/'lineage.jsonl'); health=lines(trial/'health.jsonl')
    joints=[]
    for x in ts:
        if x['topic']!='/joint_states':continue
        p=x['payload']
        try:idx=[p['name'].index(n) for n in NAMES];joints.append((x['monotonic_ns'],[p['position'][i] for i in idx],[p['velocity'][i] for i in idx]))
        except (ValueError,IndexError):pass
    starts={x['name']:x['monotonic_ns'] for x in ev if x['kind']=='phase_start'}
    ends={x['name']:x['monotonic_ns'] for x in ev if x['kind']=='phase_end'}
    phases={}
    for name,start in starts.items():
        end=ends.get(name)
        if not end:continue
        j=[x for x in joints if start<=x[0]<end]
        phases[name]={'joint_samples':len(j),'max_excursion_rad':max((max(x[1][i] for x in j)-min(x[1][i] for x in j) for i in range(6)),default=None),
          'max_velocity_rad_s':max((abs(v) for x in j for v in x[2]),default=None),
          'ros_counts':dict(collections.Counter(x['topic'] for x in ts if start<=x['monotonic_ns']<end))}
    trigger=next((x['monotonic_ns'] for x in ev if x['kind'] in ('external_stop_request','native_tracking_gate_request','health_trigger')),None)
    if trigger is None and 'sender_stall' in starts:
        received=[x['monotonic_ns'] for x in lin if x['kind']=='source_received' and x['monotonic_ns']<=starts['sender_stall']]
        trigger=max(received)+250_000_000 if received else None
    if trigger and health:trigger=next((x['monotonic_ns'] for x in health if x['kind']=='monitor_health_event'),trigger)
    pubs=[x for x in lin if x['kind']=='publish']
    leaves=collections.Counter(tip(x.get('parent')) for x in pubs)
    no_source=sum(n for sample,n in leaves.items() if sample is None)
    extra={}
    if trigger:
        after=[x for x in joints if trigger<=x[0]<=trigger+1_000_000_000]
        extra={'trigger_ns':trigger,'settled_by_1s':settled(joints,trigger)}
        if joints and after:
            before=max((x for x in joints if x[0]<=trigger),default=None,key=lambda x:x[0])
            if before:extra['joint_displacement_from_trigger_1s_rad']=max(abs(x[1][i]-before[1][i]) for x in after for i in range(6))
        output_topic='/joint_group_velocity_controller/commands' if trial.name.startswith('docker') else '/ur5_arm_controller/joint_trajectory'
        outs=[x for x in ts if x['topic']==output_topic and trigger<=x['monotonic_ns']<=trigger+1_000_000_000]
        extra['controller_outputs_first_1s']=len(outs)
        if trial.name.startswith('docker'):
            nonzero=[x for x in outs if max((abs(y) for y in x['payload']['data']),default=0)>1e-6]
            extra['nonzero_controller_outputs_first_1s']=len(nonzero)
            extra['last_nonzero_after_trigger_ms']=(nonzero[-1]['monotonic_ns']-trigger)/1e6 if nonzero else None
        else:extra['trajectory_outputs_first_1s']=[{'ms':(x['monotonic_ns']-trigger)/1e6,'points':x['payload']['points']} for x in outs[:3]]
    results[trial.name]={'exit':json.loads((trial/'exit.json').read_text()) if (trial/'exit.json').exists() else None,'phases':phases,'trigger':extra,
      'lineage':{'publishes':len(pubs),'unique_source_ids':len(leaves)-int(None in leaves),'repeated_sources':sum(1 for sample,n in leaves.items() if sample is not None and n>3),
                 'publications_without_source_id':no_source,'consume_associations':dict(collections.Counter(x.get('association') for x in lin if x['kind']=='consume'))},
      'health':health,'final_joints':joints[-1][1] if joints else None}
(ROOT/'analysis/metrics.json').write_text(json.dumps(results,indent=2,sort_keys=True))
print(json.dumps({k:{'exit':v['exit'],'trigger':{x:y for x,y in v['trigger'].items() if x!='trajectory_outputs_first_1s'}} for k,v in results.items()},indent=2))
