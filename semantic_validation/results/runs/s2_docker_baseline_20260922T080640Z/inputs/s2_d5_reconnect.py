#!/usr/bin/env python3
"""Dedicated disconnect/reconnect trial with active motion after each reference."""
from __future__ import annotations
import argparse, json, socket, time
from pathlib import Path

def emit(out,trial,event,**fields):
 rec={"record_type":"marker","trial_id":trial,"event":event,"wall_time_ns":time.time_ns(),"monotonic_ns":time.monotonic_ns(),**fields};out.open("a",encoding="utf-8").write(json.dumps(rec,sort_keys=True)+"\n");print(json.dumps(rec,sort_keys=True),flush=True)
def send(sock,out,trial,x,seconds):
 ts=time.time();emit(out,trial,"START",tracked=True,teleop=True,source_timestamp=ts,x=x,seconds=seconds);n=0;end=time.monotonic()+seconds
 while time.monotonic()<end:
  hand={"isTracked":True,"pos":{"x":x,"y":.2,"z":.3},"rot":{"x":0.,"y":0.,"z":0.,"w":1.}}
  obj={"timestamp":ts,"left_hand":hand,"right_hand":hand,"controls":{"teleop_enable":True,"right_teleop_enable":True,"grip_value":1.,"source":"s2_synthetic_tcp","trial_id":trial}}
  raw=(json.dumps(obj,separators=(",",":"))+"\n").encode();sock.sendall(raw)
  rec={"record_type":"send","trial_id":trial,"sequence":n,"sent_wall_ns":time.time_ns(),"sent_monotonic_ns":time.monotonic_ns(),"tracked":True,"teleop":True,"source_timestamp":ts,"x":x,"wire_utf8":raw.decode().rstrip("\n")};out.open("a",encoding="utf-8").write(json.dumps(rec,sort_keys=True)+"\n");n+=1;time.sleep(.05)
 emit(out,trial,"END",sends=n)
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--port",type=int,default=15008);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
 emit(a.output,"D0_RECONNECT","START",condition="idle",seconds=1.0);time.sleep(1.0);emit(a.output,"D0_RECONNECT","END")
 first=socket.create_connection(("127.0.0.1",a.port),timeout=5);emit(a.output,"CONNECTION_1","CONNECTED");send(first,a.output,"D5_FIRST_REFERENCE",.20,.8);send(first,a.output,"D5_FIRST_ACTIVE",.35,1.0);first.close();emit(a.output,"CONNECTION_1","CLOSED")
 emit(a.output,"D5_DISCONNECTED_IDLE","START",seconds=.7);time.sleep(.7);emit(a.output,"D5_DISCONNECTED_IDLE","END")
 second=socket.create_connection(("127.0.0.1",a.port),timeout=5);emit(a.output,"CONNECTION_2","CONNECTED");send(second,a.output,"D5_RECONNECT_REFERENCE",.50,.8);send(second,a.output,"D5_RECONNECT_ACTIVE",.35,1.0);second.close();emit(a.output,"CONNECTION_2","CLOSED");time.sleep(.8)
if __name__=="__main__":main()
