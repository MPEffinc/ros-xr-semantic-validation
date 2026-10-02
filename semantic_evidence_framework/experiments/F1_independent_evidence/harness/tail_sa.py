"""Follow sa_client's JSON-lines log and keep the latest app-visible action state (app side)."""
import json, os, threading, time
class SaTail:
    def __init__(self, path):
        self.path, self.latest, self.samples = path, None, []
        threading.Thread(target=self._run, daemon=True).start()
    def _run(self):
        while not os.path.exists(self.path): time.sleep(0.01)
        with open(self.path) as f:
            while True:
                line = f.readline()
                if not line: time.sleep(0.002); continue
                try: d = json.loads(line)
                except ValueError: continue
                if 'isActive' in d:
                    self.latest = d; self.samples.append(d)
                    for cb in getattr(self, 'callbacks', []): cb(d)
