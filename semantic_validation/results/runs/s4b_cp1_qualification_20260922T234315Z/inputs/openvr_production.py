import os
import time
from pathlib import Path
import openvr
import rclpy
from quest_bridge.quest_teleop import QuestTeleop
root=Path(os.environ['TRIAL_ROOT'])
rclpy.init()
node=QuestTeleop()
# Hold the original timer until the acknowledged barrier in both B0 and shim.
# This schedules the fixture only; it adds no source-state/control verdict.
node.timer.cancel()
if os.environ['MODE']!='b0':
    from trace import Publisher
    node.publisher_=Publisher(node.publisher_,'production_pose',lambda:openvr.CURRENT)
root.joinpath('production.ready').write_text('publisher constructed; spin held at source index zero\n')
while not root.joinpath('barrier.json').exists(): time.sleep(.005)
start_ns=__import__('json').loads(root.joinpath('barrier.json').read_text())['start_monotonic_ns']
while time.monotonic_ns()<start_ns: time.sleep(min(.001,(start_ns-time.monotonic_ns())/1e9))
node.timer.reset()
try:
    rclpy.spin(node)
finally:
    node.destroy_node()
