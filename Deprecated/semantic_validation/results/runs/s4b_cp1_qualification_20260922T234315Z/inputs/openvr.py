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
        index=self.call_count
        phase='idle' if index<50 else 'reference' if index<100 else 'ramp' if index<400 else 'hold' if index<500 else 'tail'
        grip=phase in ('reference','ramp','hold')
        z=0.001*min(max(index-99,0),300)
        self.valid=True
        self.default_grip=grip
        self.motion_step=[0,0,0]
        super().getDeviceToAbsoluteTrackingPose(universe,predicted_seconds,poses)
        poses[0].mDeviceToAbsoluteTracking[2][3]=3.0+z
        barrier=json.loads(Path(os.environ['TRIAL_ROOT'],'barrier.json').read_text())
        CURRENT=dict(sample_id=f'openvr:{index}', generation_id=1,
          source_timestamp_ns=time.monotonic_ns(), scheduled_ns=barrier['start_monotonic_ns']+index*20_000_000,
          phase=phase, index=index,
          native_state=dict(bPoseIsValid=bool(poses[0].bPoseIsValid),bDeviceIsConnected=True,eTrackingResult=200),
          matrix=[[float(poses[0].mDeviceToAbsoluteTracking[r][c]) for c in range(4)] for r in range(3)], grip=grip)
        with Path(os.environ['TRIAL_ROOT'],'source.jsonl').open('a') as f:
            f.write(json.dumps(CURRENT,sort_keys=True)+'\n')

def init(application_type):
    return Scheduled()
