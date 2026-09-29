#!/usr/bin/env python3
"""Observation-only Quest sideband plus native ROS PoseStamped observer."""
from __future__ import annotations

import argparse, asyncio, json, signal, threading, time
from datetime import datetime, timezone
from pathlib import Path

import rclpy
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from geometry_msgs.msg import PoseStamped


def utc(): return datetime.now(timezone.utc).isoformat()


class Log:
    def __init__(self, path):
        self.path=Path(path); self.lock=threading.Lock()
        if self.path.exists(): raise FileExistsError(f"refusing to overwrite {self.path}")
        self.path.touch()
    def put(self, record):
        with self.lock, self.path.open("a") as f:
            f.write(json.dumps(record,sort_keys=True)+"\n")


def main():
    p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True); p.add_argument('--port',type=int,required=True)
    p.add_argument('--result-dir',type=Path,required=True); p.add_argument('--topic',default='/robot_target_pose')
    a=p.parse_args(); a.result_dir.mkdir(parents=True,exist_ok=True)
    exp=Log(a.result_dir/'experiment_sideband.jsonl'); ros=Log(a.result_dir/'native_ros_observer.jsonl')
    app=FastAPI(); clients=set(); loop_box={}; count=0; latest={}

    @app.get('/health')
    async def health(): return {'status':'ok','run_id':a.run_id,'native_ros_count':count}

    @app.websocket('/experiment')
    async def endpoint(ws:WebSocket):
        await ws.accept(); clients.add(ws); loop_box['loop']=asyncio.get_running_loop()
        await ws.send_text(json.dumps({'type':'experiment_hello','schema':'spes-native-ros-sideband-v1','run_id':a.run_id}))
        exp.put({'event':'connection','state':'connected','run_id':a.run_id,'wall_utc':utc(),'monotonic_ns':time.monotonic_ns()})
        try:
            while True:
                msg=json.loads(await ws.receive_text()); data=msg.get('data') if msg.get('type')=='experiment_event' else msg
                if not isinstance(data,dict): data={'raw':data}
                latest.update({'test':data.get('test'),'trial':data.get('trial'),'control_packet_index':data.get('control_packet_index')})
                exp.put({'event':'operator_event','run_id':a.run_id,'server_wall_utc':utc(),**data})
        except WebSocketDisconnect: pass
        finally:
            clients.discard(ws); exp.put({'event':'connection','state':'disconnected','run_id':a.run_id,'wall_utc':utc(),'monotonic_ns':time.monotonic_ns()})

    rclpy.init(); node=rclpy.create_node('spes_native_hardware_observer')
    def callback(m):
        nonlocal count
        count+=1; stamp={'sec':int(m.header.stamp.sec),'nanosec':int(m.header.stamp.nanosec)}
        rec={'event':'native_ros_observed','run_id':a.run_id,'native_publish_index':count,'trial_context':dict(latest),
             'header_stamp':stamp,'frame_id':m.header.frame_id,'position':{'x':m.pose.position.x,'y':m.pose.position.y,'z':m.pose.position.z},
             'observe_wall_utc':utc(),'observe_monotonic_ns':time.monotonic_ns()}; ros.put(rec)
        ack={'type':'server_ack','run_id':a.run_id,'server_update_index':count,'callback_emitted':True,'callback_count':count,
             'last_callback_time':rec['observe_wall_utc'],'ros_header_stamp':stamp,'trial_context':rec['trial_context']}
        lp=loop_box.get('loop')
        if lp and clients:
            async def send():
                for client in list(clients):
                    try: await client.send_text(json.dumps(ack))
                    except Exception: clients.discard(client)
            lp.call_soon_threadsafe(lambda: asyncio.create_task(send()))
    node.create_subscription(PoseStamped,a.topic,callback,10)
    stop=threading.Event(); signal.signal(signal.SIGTERM,lambda *_:stop.set()); signal.signal(signal.SIGINT,lambda *_:stop.set())
    server=uvicorn.Server(uvicorn.Config(app,host='0.0.0.0',port=a.port,
        ssl_keyfile='/tmp/spes_overlay/teleop/key.pem',ssl_certfile='/tmp/spes_overlay/teleop/cert.pem',log_level='warning'))
    thread=threading.Thread(target=server.run,daemon=True); thread.start()
    while thread.is_alive() and not stop.wait(.02): rclpy.spin_once(node,timeout_sec=.02)
    server.should_exit=True; thread.join(5); node.destroy_node(); rclpy.shutdown()
    (a.result_dir/'sideband_summary.json').write_text(json.dumps({'run_id':a.run_id,'native_ros_count':count,'clean_shutdown':True},indent=2)+'\n')
    return 0
if __name__=='__main__': raise SystemExit(main())
