"""D3 source-receipt silence state; a tick is never a source sample.

Pure logic shared by prospective source, oracle and controller placements.
No ROS or stop actuator is imported here. A caller must prove that a receipt
belongs to a distinct real source sample, not a repeated cached publication.
"""

LIMIT_NS = 250_000_000


class SourceSilence:
    def __init__(self):
        self.last_sample_id = None
        self.last_receipt_ns = None
        self.last_active = False
        self.last_tracked = None
        self.generation_id = None
        self.genuine_receipt_count = 0
        self.duplicate_count = 0

    def receive(self, sample_id, receipt_ns, active, tracked, generation_id):
        """Record a *new* source sample once, using a verified local clock."""
        if sample_id is None or receipt_ns is None:
            raise ValueError('real source sample requires exact ID and receipt time')
        if sample_id == self.last_sample_id:
            self.duplicate_count += 1
            return False
        if self.last_receipt_ns is not None and receipt_ns < self.last_receipt_ns:
            raise ValueError('source receipt time went backwards')
        self.last_sample_id = sample_id
        self.last_receipt_ns = int(receipt_ns)
        self.last_active = bool(active)
        self.last_tracked = bool(tracked)
        self.generation_id = generation_id
        self.genuine_receipt_count += 1
        return True

    def tick(self, now_ns):
        """Evaluate silence without changing the source cache or its timestamp."""
        if self.last_receipt_ns is None:
            return {'state': 'UNOBSERVABLE', 'trigger_ns': None,
                    'last_sample_id': None}
        trigger_ns = self.last_receipt_ns + LIMIT_NS
        if not self.last_active or not self.last_tracked:
            state = 'NO_ACTIVE_CONTROL'
        elif now_ns > trigger_ns:
            state = 'SOURCE_SILENCE'
        else:
            state = 'FRESH'
        return {'state': state, 'trigger_ns': trigger_ns,
                'last_sample_id': self.last_sample_id,
                'last_receipt_ns': self.last_receipt_ns,
                'age_ns': int(now_ns) - self.last_receipt_ns,
                'genuine_receipt_count': self.genuine_receipt_count,
                'duplicate_count': self.duplicate_count}
