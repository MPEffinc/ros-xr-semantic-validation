#!/usr/bin/env python3
"""M3_ordering stop arms (R18). Trigger: the same runtime evidence and latch as R10 stop_arm.py.
  CUR  R10 HOLD behaviour: pause_servo(true) + JTC one-point hold at the measured joints, published DIRECTLY on the
       controller topic, at once, on the pause ack and +0.1 s (shared M39 core).
  MUX  exclusive writer at the controller boundary: topic_tools mux (ros-jazzy-topic-tools 1.3.4) is the only writer to
       /ur5_arm_controller/joint_trajectory, inputs /m3/servo_out (Servo, remapped) and /m3/hold_in. On trigger: request
       select(/m3/hold_in) and pause_servo(true); hold messages are published on /m3/hold_in at once, on the select ack
       and +0.1 s. Until the select ack, Servo output can still pass the mux.
Args: <CUR|MUX> <log> <ev_fifo> <end_s> [mux_select_service]   env P1_T0_NS, M39_HARNESS"""
import os, sys, time
import rclpy
from trajectory_msgs.msg import JointTrajectory
sys.path.insert(0, os.environ.get("M39_HARNESS", "/m39/harness"))
from m39_transition import TransitionCore
from m39_evidence import Evidence
MODE, LOG, FIFO, END = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]); SEL = sys.argv[5] if len(sys.argv) > 5 else "/m3_mux/select"
T0 = int(os.environ["P1_T0_NS"]) / 1e9
rclpy.init(); node = rclpy.create_node("m3_stop_arm")
core = TransitionCore(node, LOG); core.state = "ACTIVE"
if MODE == "MUX":
    from topic_tools_interfaces.srv import MuxSelect
    core.jtc = node.create_publisher(JointTrajectory, "/m3/hold_in", 10)   # holds go to the mux hold input
    sel = node.create_client(MuxSelect, SEL)
    def select_hold():
        req = MuxSelect.Request(); req.topic = "/m3/hold_in"; core.log("mux_select_call", service_ready=sel.service_is_ready())
        f = sel.call_async(req)
        f.add_done_callback(lambda fu: (core.log("mux_select_ack", ok=fu.result() is not None, prev=getattr(fu.result(), "prev_topic", None)),
                                        core.state in ("HOLDING", "HELD") and core.hold("mux_select_ack")))
ev = Evidence(FIFO); st = {"armed": False, "prev": 0.0, "done": False}
core.log("mode", mode=MODE)
def tick():
    now = time.time(); ok, age, fo, fl, bad = ev.state()
    if bad is not None and bad > st["prev"]: ok = False
    st["prev"] = now
    if not st["armed"] and ok and now - T0 > 1.0: st["armed"] = True; core.log("armed")
    if st["armed"] and not st["done"] and not ok:
        st["done"] = True; core.log("trigger", ev_age=age)
        if MODE == "MUX": select_hold()
        core.interrupt("evidence_not_ok")
    if now - T0 > END: core.log("final"); raise SystemExit(0)
node.create_timer(0.005, tick)
try: rclpy.spin(node)
except (SystemExit, KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
