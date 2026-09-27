"""Observation-only persistence of a DDS match before receiver timers spin."""
import json


def record_monitor_match(root, match, logger):
    # trace.log owns the event's monotonic_ns field. Keeping the measured
    # match instant separate avoids a duplicate-key crash in that logger.
    if 'monotonic_ns' in match or 'kind' in match:
        raise ValueError('reserved lineage log key in DDS match')
    logger('pre_spin_monitor_dds_match', **match)
    (root / 'monitor_dds_match.ready').write_text(json.dumps(match))
