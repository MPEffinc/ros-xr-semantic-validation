"""Host brackets container CLOCK_MONOTONIC on persistent stdio; no time correction."""
import json,os,shlex,subprocess,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
code="import sys,time,json,os; from pathlib import Path; print(json.dumps(dict(boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),ns=os.readlink('/proc/self/ns/time'))),flush=True); [(print(time.monotonic_ns(),flush=True)) for line in sys.stdin]"
out={'host':{'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'ns':os.readlink('/proc/self/ns/time')},'containers':{}}
for distro in ['humble','jazzy']:
    argv=['sg','docker','-c',shlex.join(['docker','run','--rm','-i','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--entrypoint','python3',f's4b-rosmonitoring-{distro}:20260922','-u','-c',code])]
    with (root/'commands.jsonl').open('a') as f:f.write(json.dumps({'argv':argv,'purpose':'clock_bracket'})+'\n')
    p=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    identity=json.loads(p.stdout.readline()); rows=[]
    for i in range(50):
        start=time.monotonic_ns(); p.stdin.write('tick\n'); p.stdin.flush()
        remote=int(p.stdout.readline()); end=time.monotonic_ns()
        rows.append({'host_start_ns':start,'container_ns':remote,'host_end_ns':end,
           'offset_lower_ns':remote-end,'offset_upper_ns':remote-start,'uncertainty_ns':(end-start)/2})
    p.stdin.close(); p.wait(timeout=10)
    out['containers'][distro]={'identity':identity,'samples':rows,'stderr':p.stderr.read(),
      'same_boot_namespace':identity==out['host'],'max_uncertainty_ns':max(r['uncertainty_ns'] for r in rows),
      'zero_in_all_brackets':all(r['offset_lower_ns']<=0<=r['offset_upper_ns'] for r in rows)}
(root/'analysis/clock.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:{n:v for n,v in x.items() if n!='samples'} for k,x in out['containers'].items()},indent=2))
