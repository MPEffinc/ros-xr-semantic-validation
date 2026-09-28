import json, sys
from pathlib import Path
d = Path(sys.argv[1])
st = [json.loads(x) for x in (d / 'monitor_full_status.jsonl').read_text().splitlines() if x.strip()]
cb = [s['event']['time'] for s in st if s.get('status') == 'event']
gaps = sorted((b - a) * 1000 for a, b in zip(cb[1:], cb[2:]))
print(d.name, 'events', len(cb), 'gap p50 %.1f p99 %.1f max %.1f' % (gaps[len(gaps)//2], gaps[int(.99*len(gaps))], gaps[-1]),
      'n>60ms', sum(g > 60 for g in gaps))
