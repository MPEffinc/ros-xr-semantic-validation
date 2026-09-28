"""Post-capture observation gate for exact real-source receiver coverage.

This reads traces only after control capture; it never gates source inputs.
"""


def check_receiver_coverage(sent, lineage):
    expected = [f'docker:{row["index"]}' for row in sent if row.get('sent')]
    seen = [(row.get('metadata') or {}).get('sample_id') for row in lineage
            if row.get('kind') == 'source_received']
    stored = [row.get('sample_id') for row in lineage
              if row.get('kind') == 'original_receiver_source_stored']
    return dict(ok=(seen == expected and stored == expected),
                expected_count=len(expected), seen_count=len(seen),
                stored_count=len(stored), expected_ids=expected,
                seen_ids=seen, stored_ids=stored)
