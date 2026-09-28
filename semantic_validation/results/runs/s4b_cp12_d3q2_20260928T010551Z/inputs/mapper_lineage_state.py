"""Observation-only identity of the source last applied by the original mapper.

No policy predicate lives here. `applied` is set only after the original
callback returns. A rejected candidate never changes the timer's parent.
"""
from threading import RLock


class MapperLineageState:
    def __init__(self):
        self._lock = RLock()
        self.last_observed = None
        self.last_accepted = None
        self.last_applied = None
        self.last_rejected = None
        self.applied_snapshot = None

    def observe(self, edge):
        with self._lock:
            self.last_observed = edge

    def reject(self, edge):
        with self._lock:
            self.last_rejected = edge

    def apply_after_original_callback(self, edge, state_snapshot):
        with self._lock:
            self.last_accepted = edge
            self.last_applied = edge
            self.applied_snapshot = dict(state_snapshot)

    def timer_parent(self):
        with self._lock:
            return self.last_applied

    def snapshot(self):
        with self._lock:
            return dict(last_observed=self.last_observed,
                        last_accepted=self.last_accepted,
                        last_applied=self.last_applied,
                        last_rejected=self.last_rejected,
                        applied_snapshot=self.applied_snapshot)
