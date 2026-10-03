# M39_stop (R10): existing controller-level stop methods on the M39 path
- `arms/stop_arm.py` (HOLD = shared M39 core; DECEL_TOPIC = external JTC-formula deceleration on the topic)
- `harness/trial_stop.sh`, `run_stop.py`, `schedule_stop.csv`, `scenarios/` (I3, QF, I3h, QFh)
- `jtc_action/` + `config/jtc_decel_on_cancel.yaml` + `run_action.py` + `schedule_action.csv`: standalone JTC action verification
- `analysis/analyze_stop.py`, `analysis/analyze_action.py`; raw in `raw/` (ignored)
