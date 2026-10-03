#!/usr/bin/env python3
"""M12_receiver B1: edit a COPY of Docker_Teleop quest_controller_receiver.py @64cbdde (the upstream has no license,
so only this edit script is stored). Changes (all marked M12-B1):
 - _store_payload: keep, with the latest state, the receiver receipt time (ROS clock), a receipt counter, and the
   producer's 'seq'/'session'/'timestamp' if present;
 - _publish_loop: additionally publish m12r_prov_msgs/ReceivedPoseStatesProv on '<output_topic>_prov' carrying the
   SAME state message plus that provenance and a 'neutral' flag when the stale/startup neutral state is published.
The original topics and messages are unchanged. Usage: apply_receiver_provenance.py <in.py> <out.py>"""
import sys
s = open(sys.argv[1]).read()
def edit(old, new):
    global s; assert old in s, old[:60]; s = s.replace(old, new, 1)
edit("from teleop_bridge_msgs.msg import ReceivedPoseStates\n",
     "from teleop_bridge_msgs.msg import ReceivedPoseStates\nfrom m12r_prov_msgs.msg import ReceivedPoseStatesProv  # M12-B1\n")
edit("        self.right_pub = self.create_publisher(ReceivedPoseStates, right_output_topic, 20)\n",
     "        self.right_pub = self.create_publisher(ReceivedPoseStates, right_output_topic, 20)\n"
     "        self.prov_pub = self.create_publisher(ReceivedPoseStatesProv, output_topic + '_prov', 20)  # M12-B1\n"
     "        self._prov = {'rx_count': 0, 'rx_stamp': None, 'seq': None, 'session': '', 'src_time': None}  # M12-B1\n")
edit("        now = time.monotonic()\n\n        with self._state_lock:\n            self._latest_state = parsed_state\n",
     "        now = time.monotonic()\n"
     "        rx_stamp = self.get_clock().now().to_msg()  # M12-B1: packet receipt (receiver clock)\n"
     "        seq = payload.get('seq') if isinstance(payload, dict) else None  # M12-B1\n"
     "        session = payload.get('session') if isinstance(payload, dict) else None  # M12-B1\n"
     "        src_time = payload.get('timestamp') if isinstance(payload, dict) else None  # M12-B1\n\n"
     "        with self._state_lock:\n"
     "            self._prov = {'rx_count': self._prov['rx_count'] + 1, 'rx_stamp': rx_stamp,  # M12-B1\n"
     "                          'seq': seq if isinstance(seq, int) else None, 'session': str(session) if session is not None else '',\n"
     "                          'src_time': float(src_time) if isinstance(src_time, (int, float)) else None}\n"
     "            self._latest_state = parsed_state\n")
edit("            state = self._latest_state if not stale else self._neutral_state(source=\"stale_timeout\")\n",
     "            state = self._latest_state if not stale else self._neutral_state(source=\"stale_timeout\")\n"
     "            prov = dict(self._prov)  # M12-B1\n")
edit("        msg = self._make_msg(state, now_msg)\n        self.pub.publish(msg)\n",
     "        msg = self._make_msg(state, now_msg)\n        self.pub.publish(msg)\n"
     "        p = ReceivedPoseStatesProv(); p.state = msg  # M12-B1: same message object content\n"
     "        p.neutral = stale or str(state['source']).endswith('startup')\n"
     "        p.rx_count = prov['rx_count']\n"
     "        if prov['rx_stamp'] is not None: p.rx_stamp = prov['rx_stamp']\n"
     "        p.src_seq_valid = prov['seq'] is not None and prov['session'] != ''\n"
     "        p.src_seq = prov['seq'] if prov['seq'] is not None else -1\n"
     "        p.src_session = prov['session']\n"
     "        p.src_time_valid = prov['src_time'] is not None\n"
     "        p.src_time = prov['src_time'] if prov['src_time'] is not None else 0.0\n"
     "        self.prov_pub.publish(p)  # M12-B1\n")
open(sys.argv[2], "w").write(s); print("patched")
