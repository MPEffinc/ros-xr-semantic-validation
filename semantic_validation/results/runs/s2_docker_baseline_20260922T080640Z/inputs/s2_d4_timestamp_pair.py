#!/usr/bin/env python3
"""Dedicated fresh-versus-old source-time trial with opposite, active deltas."""
from __future__ import annotations
import argparse, json, socket, time
from pathlib import Path

def emit(out, trial, event, **fields):
    rec={"record_type":"marker","trial_id":trial,"event":event,"wall_time_ns":time.time_ns(),"monotonic_ns":time.monotonic_ns(),**fields}
    with out.open("a",encoding="utf-8") as f: f.write(json.dumps(rec,sort_keys=True)+"\n")
    print(json.dumps(rec,sort_keys=True),flush=True)

def wire(trial, tracked, source_timestamp, x):
    hand={"isTracked":tracked,"pos":{"x":x,"y":.20,"z":.30},"rot":{"x":0.,"y":0.,"z":0.,"w":1.}}
    return {"timestamp":source_timestamp,"left_hand":hand,"right_hand":hand,"controls":{"teleop_enable":True,"right_teleop_enable":True,"grip_value":1.,"source":"s2_synthetic_tcp","trial_id":trial}}

def send(sock,out,trial,ts,x,seconds):
    emit(out,trial,"START",tracked=True,teleop=True,source_timestamp=ts,x=x,seconds=seconds)
    n=0; until=time.monotonic()+seconds
    while time.monotonic()<until:
        obj=wire(trial,True,ts,x); raw=(json.dumps(obj,separators=(",",":"))+"\n").encode()
        sock.sendall(raw)
        rec={"record_type":"send","trial_id":trial,"sequence":n,"sent_wall_ns":time.time_ns(),"sent_monotonic_ns":time.monotonic_ns(),"tracked":True,"teleop":True,"source_timestamp":ts,"x":x,"wire_utf8":raw.decode().rstrip("\n")}
        with out.open("a",encoding="utf-8") as f:f.write(json.dumps(rec,sort_keys=True)+"\n")
        n+=1; time.sleep(.05)
    emit(out,trial,"END",sends=n)

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--port",type=int,default=15007);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
    emit(a.output,"D0_TIMESTAMP_PAIR","START",condition="idle",seconds=1.0);time.sleep(1.0);emit(a.output,"D0_TIMESTAMP_PAIR","END")
    s=socket.create_connection(("127.0.0.1",a.port),timeout=5);emit(a.output,"CONNECTION_TIMESTAMP","CONNECTED")
    send(s,a.output,"D4_OLD_REFERENCE",1.0,.20,.8);send(s,a.output,"D4_OLD_ACTIVE",1.0,.35,1.0)
    emit(a.output,"D4_RESET","START",seconds=.6);time.sleep(.6);emit(a.output,"D4_RESET","END")
    now=time.time();send(s,a.output,"D4_FRESH_REFERENCE",now,.50,.8);send(s,a.output,"D4_FRESH_ACTIVE",now+.8,.35,1.0)
    s.close();emit(a.output,"CONNECTION_TIMESTAMP","CLOSED");time.sleep(.8)
if __name__=="__main__":main()
