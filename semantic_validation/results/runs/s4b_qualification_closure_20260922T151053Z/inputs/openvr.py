"""S3 fake dependency with an externally scheduled qualification fixture."""
import importlib.util
import json
import os
import time
from pathlib import Path
spec=importlib.util.spec_from_file_location('s3_fake','/harness/openvr.py')
base=importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
for name in dir(base):
    if not name.startswith('__'):
        globals()[name]=getattr(base,name)
CURRENT=None

class Scheduled(base._FakeVRSystem):
    def getDeviceToAbsoluteTrackingPose(self, universe, predicted_seconds, poses):
        global CURRENT
        phase=json.loads(Path(os.environ['TRIAL_ROOT'],'phase.json').read_text())
        self.valid=phase.get('tracked',True)
        self.default_grip=phase.get('teleop',False)
        self.motion_step=[0,0,0]
        super().getDeviceToAbsoluteTrackingPose(universe,predicted_seconds,poses)
        poses[0].mDeviceToAbsoluteTracking[2][3]=3.0+phase.get('z',0.0)
        CURRENT=dict(sample_id=f'openvr:{self.call_count}', generation_id=phase['generation'],
          source_timestamp_ns=time.monotonic_ns(), phase=phase['name'],
          native_state=dict(bPoseIsValid=bool(poses[0].bPoseIsValid),bDeviceIsConnected=True,eTrackingResult=200),
          matrix=[[float(poses[0].mDeviceToAbsoluteTracking[r][c]) for c in range(4)] for r in range(3)], grip=self.default_grip)
        with Path(os.environ['TRIAL_ROOT'],'source.jsonl').open('a') as f:
            f.write(json.dumps(CURRENT,sort_keys=True)+'\n')

def init(application_type):
    return Scheduled()
