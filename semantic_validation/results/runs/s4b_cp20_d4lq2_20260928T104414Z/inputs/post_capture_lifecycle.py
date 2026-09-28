"""Trial-owned producer lifecycle after the fixed six-second outcome capture.

This is not an XR validity/freshness predicate. All original messages emitted
before this marker remain in the monitor association denominator.
"""
from pathlib import Path


def capture_has_ended(root):
    return (Path(root) / 'capture_end.ready').is_file()
