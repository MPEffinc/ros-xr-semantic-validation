"""No-Gazebo child-exit and generated-monitor wiring inspection."""
import ast
import json
import os
import sys
import tempfile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
helper = ROOT / 'inputs/child_supervisor.sh'
launch = (ROOT / 'inputs/launch.sh').read_text()
probe = (ROOT / 'inputs/d1_probe.py').read_text()
stop_adapter = (ROOT / 'inputs/d1_stop_adapter.py').read_text()
nodes = (ROOT / 'inputs/d1_nodes.py').read_text()


def shell(script):
    return subprocess.run(['bash', '-c', f'source {helper}; {script}'],
                          capture_output=True, text=True)


failed = shell('(exit 7) & child=$!; wait_required_finished "$child" sender')
passed = shell('(exit 0) & child=$!; wait_required_finished "$child" sender')
missing = shell('assert_required_running 99999999 monitor')
running = shell('sleep 1 & child=$!; assert_required_running "$child" oracle')
assert failed.returncode == 7 and passed.returncode == 0
assert missing.returncode == 17 and running.returncode == 0
assert 'wait_required_finished "$sender_pid" sender' in launch
assert 'assert_required_running "${pids[$i]}" "${labels[$i]}"' in launch
assert "len(sent) != 120" in probe and "list(range(120))" in probe
assert "sender.done" in probe
assert 'participant_clocks()' in probe
assert 'participant_entry.py "$label" "$@"' in launch
assert 'start stop_adapter python3 /code/d1_stop_adapter.py' in launch
assert 'self.destroy_publisher(original_pub)' in nodes
assert 'd1_lossless_stripper' in probe
assert all(field not in stop_adapter for field in ('isTracked', 'source_timestamp_ns', 'generation_id', 'native_state'))
with tempfile.TemporaryDirectory(prefix='s4b_cp4_clock_') as temp:
    env = os.environ.copy()
    env['TRIAL_ROOT'] = temp
    entry = subprocess.run([sys.executable, str(ROOT / 'inputs/participant_entry.py'), 'unit', sys.executable, '-c', 'print(123)'], env=env, capture_output=True, text=True)
    record = json.loads((Path(temp) / 'participant_clock_unit.json').read_text())
    assert entry.returncode == 0 and entry.stdout.strip() == '123'
    assert record['clock'] == 'CLOCK_MONOTONIC' and record['label'] == 'unit'

monitors = []
for ident, topic in [('d1_full_guard', '/s4b/d1/envelope'),
                     ('d1_native_guard', '/s4b/d1/native_input')]:
    source = ROOT / 'monitor_ws/src/monitor/monitor' / f'{ident}.py'
    tree = ast.parse(source.read_text())
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'INTERFACES'
                              for t in n.targets))
    interfaces = ast.literal_eval(assignment.value)
    assert len(interfaces) == 1
    iface = interfaces[0]
    assert iface['name'] == topic and iface['remapped_name'] == topic + '_mon'
    assert iface['action'] == 'filter'
    monitors.append({'name': ident, 'input': iface['remapped_name'],
                     'forwarded_output': iface['name'], 'action': iface['action']})

summary = dict(status='PASS_STATIC_AND_CHILD_UNIT_ONLY',
               child_exit_failure=failed.returncode,
               child_exit_success=passed.returncode,
               missing_monitor=missing.returncode,
               running_oracle=running.returncode,
               sender_completion_asserted_by_probe=True,
               participant_clock_wrapper_passed=True,
               stop_adapter_has_no_xr_semantic_predicate=True,
               generated_official_interfaces=monitors,
               caveat='No actual ROS DDS graph, oracle connection or Gazebo in this test')
(ROOT / 'analysis/launcher_preflight.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, sort_keys=True))
