import openvr
import rclpy
from quest_bridge.quest_teleop import QuestTeleop
from trace import Publisher
rclpy.init()
node=QuestTeleop()
node.publisher_=Publisher(node.publisher_,'production_pose',lambda:openvr.CURRENT)
try:
    rclpy.spin(node)
finally:
    node.destroy_node()
