"""Observation only: exact serialized ROS payload edges and callback selection."""
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from rclpy.serialization import serialize_message
from rosidl_runtime_py.convert import message_to_ordereddict

ROOT = Path(os.environ['TRIAL_ROOT'])
ROOT.mkdir(parents=True, exist_ok=True)
LOCK = threading.RLock()
EDGES = {}
COUNTS = {}

def log(kind, **data):
    with LOCK, (ROOT / 'lineage.jsonl').open('a') as f:
        f.write(json.dumps(dict(kind=kind, monotonic_ns=time.monotonic_ns(), **data), sort_keys=True)+'\n')

def digest(msg):
    return hashlib.sha256(json.dumps(message_to_ordereddict(msg),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def bind(stage, msg, parent):
    with LOCK:
        COUNTS[stage] = COUNTS.get(stage, 0)+1
        command_id = f'{stage}:{COUNTS[stage]}'
        h = digest(msg)
        edge = dict(command_id=command_id, parent=parent, payload_sha256=h)
        EDGES.setdefault(h, []).append(edge)
        log('publish', stage=stage, **edge, payload=message_to_ordereddict(msg))
        return edge

def consume(stage, msg):
    matches = EDGES.get(digest(msg), [])
    edge = matches[0] if len(matches)==1 else None
    log('consume', stage=stage, payload_sha256=digest(msg), exact_parent=edge,
        association='EXACT_CANONICAL_ROS_FIELDS' if edge else 'UNKNOWN', matches=len(matches))
    return edge

class Publisher:
    def __init__(self, original, stage, parent):
        self.original, self.stage, self.parent = original, stage, parent
    def publish(self, msg):
        before = message_to_ordereddict(msg)
        bind(self.stage, msg, self.parent())
        assert message_to_ordereddict(msg)==before
        self.original.publish(msg)
    def __getattr__(self, name):
        return getattr(self.original, name)

log('clock', boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    time_namespace=os.readlink('/proc/self/ns/time'), clock='CLOCK_MONOTONIC')
