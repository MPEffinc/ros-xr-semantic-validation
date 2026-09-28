"""Observation-only hash for the original receiver's Python source dict.

trace.digest() is intentionally ROS-message-specific and must not be used on
source dictionaries. This helper never alters payload or control decisions.
"""
import hashlib
import json


def source_payload_sha256(payload):
    if not isinstance(payload, dict):
        raise TypeError('source payload must be a Python dict')
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                           allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest()
