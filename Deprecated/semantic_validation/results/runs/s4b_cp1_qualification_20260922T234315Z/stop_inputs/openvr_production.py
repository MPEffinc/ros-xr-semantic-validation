import os
import time
from pathlib import Path
import openvr
import rclpy
from quest_bridge.quest_teleop import QuestTeleop
root=Path(os.environ['TRIAL_ROOT'])
rclpy.init()
node=QuestTeleop()
if os.environ['MODE']!='b0':
    from trace import Publisher
    node.publisher_=Publisher(node.publisher_,'production_pose',lambda:openvr.CURRENT)
root.joinpath('production.ready').write_text('publisher constructed; spin held at source index zero\n')
while not root.joinpath('barrier.json').exists(): time.sleep(.005)
try:
    rclpy.spin(node)
finally:
    node.destroy_node()
