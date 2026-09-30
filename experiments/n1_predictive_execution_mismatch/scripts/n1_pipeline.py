#!/usr/bin/env python3
"""N1 live pipeline for one trial (runs inside the n1sim container; wall-clock stamps, sim stamps logged).

operator (synthetic, scripted EE twist) -> [delay A] -> [shared autonomy F] -> [CBF safety filter C]
  -> /servo_node/delta_twist_cmds -> MoveIt Servo (collision D, smoothing E when enabled) -> JTC -> Gazebo.
Logs every stage + Servo output + Servo status + /joint_states to JSONL with sim-time receive stamps.

Usage: n1_pipeline.py --out FILE --delay_ms D --filter 0/1 --sa 0/1 --obstacle 0/1 --seed S
"""
import argparse, json, math, random, sys, time, collections
import numpy as np, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import TwistStamped, Pose
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from moveit_msgs.msg import ServoStatus, PlanningScene, CollisionObject
from shape_msgs.msg import SolidPrimitive
from std_srvs.srv import SetBool
from builtin_interfaces.msg import Duration
sys.path.insert(0, '/scripts'); from ur5_fk import fk, ARM

HOME = [0.0, -1.2, 1.4, -1.77, -1.57, 0.0]  # overridable with --home
# Scenario in base_link (pre-registered): (t_start, t_end, v_xyz m/s)
PHASES = [(0.0, 2.0, (0.08, 0.0, 0.0)), (2.0, 5.0, (0.0, 0.0, -0.08)), (5.0, 8.0, (0.0, 0.10, 0.0)), (8.0, 10.0, (0.0, 0.0, 0.0))]
DT = 0.02  # operator/display tick 50 Hz

class P(Node):
    def __init__(s, a):
        # Wall clock on purpose: Servo integrates on its own wall-time period, while Gazebo runs below real time,
        # so operator ticks and all log stamps use the node's system clock (sim stamps are logged separately).
        super().__init__('n1_pipeline')
        s.a = a; s.log = open(a.out, 'w'); s.q = None; s.q_t = None
        s.rng = random.Random(a.seed); s.noise = [s.rng.gauss(0, 0.004) for _ in range(3)]
        s.pub = s.create_publisher(TwistStamped, '/servo_node/delta_twist_cmds', 10)
        s.traj_pub = s.create_publisher(JointTrajectory, '/ur5_arm_controller/joint_trajectory', 10)
        s.scene_pub = s.create_publisher(PlanningScene, '/monitored_planning_scene', 10)
        s.create_subscription(JointState, '/joint_states', s.on_js, 50)
        s.create_subscription(JointTrajectory, '/ur5_arm_controller/joint_trajectory', s.on_cmd, 50)
        s.create_subscription(ServoStatus, '/servo_node/status', s.on_status, 50)
        s.pause = s.create_client(SetBool, '/servo_node/pause_servo')
        s.fifo = collections.deque(); s.t0 = None
    def now(s): return s.get_clock().now().nanoseconds * 1e-9
    def w(s, kind, **kw): kw['kind'] = kind; kw['t'] = s.now(); s.log.write(json.dumps(kw) + '\n')
    def on_js(s, m):
        d = dict(zip(m.name, m.position))
        if all(j in d for j in ARM):
            s.q = [d[j] for j in ARM]; s.q_t = s.now()
            s.w('js', q=s.q, stamp=m.header.stamp.sec + m.header.stamp.nanosec * 1e-9)
    def on_cmd(s, m):
        if not m.points or m.header.frame_id == 'n1_reset': return
        idx = [m.joint_names.index(j) for j in ARM] if all(j in m.joint_names for j in ARM) else None
        if idx is None: return
        p = m.points[0]
        s.w('servo_out', q=[p.positions[i] for i in idx], dq=[p.velocities[i] for i in idx] if p.velocities else None,
            stamp=m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, tfs=p.time_from_start.sec + p.time_from_start.nanosec * 1e-9)
    def on_status(s, m): s.w('status', code=int(m.code), msg=m.message)
    # --- helpers -----------------------------------------------------------------------------------------
    def call_pause(s, v):
        ok = False
        for _ in range(3):
            if not s.pause.wait_for_service(timeout_sec=5): continue
            f = s.pause.call_async(SetBool.Request(data=v)); rclpy.spin_until_future_complete(s, f, timeout_sec=5)
            if f.done() and f.result() is not None and f.result().success: ok = True; break
        s.w('pause_call', data=v, ok=ok); return ok
    def spin_for(s, secs):
        end = s.now() + secs
        while s.now() < end: rclpy.spin_once(s, timeout_sec=0.01)
    def reset(s):
        s.call_pause(True)
        jt = JointTrajectory(); jt.header.frame_id = 'n1_reset'; jt.joint_names = ARM
        pt = JointTrajectoryPoint(positions=list(s.a.home), time_from_start=Duration(sec=2)); jt.points = [pt]
        end = s.now() + 30.0; last = 0.0
        while s.now() < end:
            if s.now() - last > 1.0:
                s.traj_pub.publish(jt); last = s.now()  # stamp 0 = start now (controller runs on sim time)
            rclpy.spin_once(s, timeout_sec=0.02)
            if max(abs(a - b) for a, b in zip(s.q, s.a.home)) < 0.002: break
        s.reset_residual = max(abs(a - b) for a, b in zip(s.q, s.a.home))
        s.spin_for(0.5); s.call_pause(False); s.spin_for(1.0)
    def scene(s, add):
        ps = PlanningScene(); ps.is_diff = True
        co = CollisionObject(); co.id = 'n1_box'; co.header.frame_id = 'base_link'
        if add:
            pr = SolidPrimitive(type=SolidPrimitive.BOX, dimensions=[0.20, 0.06, 0.30])
            po = Pose(); po.position.x, po.position.y, po.position.z = (np.array(s.p_home_scene) + np.array(s.a.box_rel)).tolist(); po.orientation.w = 1.0
            co.primitives = [pr]; co.primitive_poses = [po]; co.operation = CollisionObject.ADD
        else:
            co.operation = CollisionObject.REMOVE
        ps.world.collision_objects = [co]
        for _ in range(5): s.scene_pub.publish(ps); s.spin_for(0.1)
    # --- one trial ---------------------------------------------------------------------------------------
    def run(s):
        while s.q is None: rclpy.spin_once(s, timeout_sec=0.1)
        s.reset(); p_home, _ = fk(s.q); s.p_home_scene = p_home.tolist(); s.scene(bool(s.a.obstacle))
        s.phases = json.loads(s.a.phases) if s.a.phases else PHASES
        s.w('meta', args=vars(s.a), home_ee=p_home.tolist(), phases=s.phases, reset_residual_rad=s.reset_residual)
        s.t0 = s.now(); nxt = s.t0
        while s.now() - s.t0 < s.a.t_run:
            rclpy.spin_once(s, timeout_sec=0.002)
            if s.now() < nxt: continue
            nxt += DT; tr = s.now() - s.t0
            v = np.zeros(3)
            for a0, a1, vv in s.phases:
                if a0 <= tr < a1: v = np.array(vv) + (np.array(s.noise) if any(vv) else 0)
            s.w('op', v=v.tolist(), tr=tr)
            s.fifo.append((s.now() + s.a.delay_ms / 1000.0, v))
            v_d = None
            while s.fifo and s.fifo[0][0] <= s.now(): v_d = s.fifo.popleft()[1]
            if v_d is None: continue
            s.w('after_delay', v=v_d.tolist())
            p, _ = fk(s.q); age = s.now() - s.q_t
            v_sa = v_d.copy(); sa_on = False
            if s.a.sa and s.a.sa_t0 <= tr < s.a.sa_t1:   # shared autonomy: blend toward the policy's goal
                g = np.array(p_home) + np.array(s.a.sa_goal)
                u_pol = np.clip(1.0 * (g - p), -0.10, 0.10); v_sa = (1 - s.a.sa_alpha) * v_d + s.a.sa_alpha * u_pol; sa_on = True
            s.w('after_sa', v=v_sa.tolist(), active=sa_on)
            v_f = v_sa.copy(); f_on = False
            if s.a.filter:                   # first-order CBF on x: dx/dt <= gamma (x_max - x)
                xmax = p_home[0] + s.a.xmax_rel; bound = s.a.gamma * (xmax - p[0])
                if v_f[0] > bound: v_f[0] = bound; f_on = True
            s.w('after_filter', v=v_f.tolist(), active=f_on, state_age=age)
            m = TwistStamped(); m.header.stamp = s.get_clock().now().to_msg(); m.header.frame_id = 'base_link'
            m.twist.linear.x, m.twist.linear.y, m.twist.linear.z = map(float, v_f); s.pub.publish(m)
        s.spin_for(1.0); s.scene(False); s.log.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True); ap.add_argument('--delay_ms', type=float, default=0)
    ap.add_argument('--filter', type=int, default=0); ap.add_argument('--sa', type=int, default=0)
    ap.add_argument('--obstacle', type=int, default=0); ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--xmax_rel', type=float, default=0.15); ap.add_argument('--gamma', type=float, default=2.0)
    ap.add_argument('--sa_alpha', type=float, default=0.4); ap.add_argument('--sa_goal', type=float, nargs=3, default=[-0.03, 0.0, 0.0]); ap.add_argument('--sa_t0', type=float, default=4.0); ap.add_argument('--sa_t1', type=float, default=9.0)
    ap.add_argument('--home', type=float, nargs=6, default=HOME); ap.add_argument('--t_run', type=float, default=10.0); ap.add_argument('--phases', default='')
    ap.add_argument('--box_rel', type=float, nargs=3, default=[0.33, 0.0, 0.0])
    a = ap.parse_args(); rclpy.init(); n = P(a); n.run(); rclpy.shutdown()
if __name__ == '__main__': main()
