# M39_decel (R09): logging-only MoveIt Servo build and collision-scale measurement
- `instr/moveit_servo_2.12.4_m39_logging.patch` — the only source change (logging); `build_ws/` (ignored) holds the build.
- `harness/trial_decel.sh` — frozen M39_pilot trial.sh + optional Servo overlay; `run_decel.py`; `schedule_decel.csv`.
- `analysis/analyze_decel.py` — imports the frozen `M39_pilot/analysis/analyze_m39.py`.
- `results/` — probe comparison (instrumented vs stock) and formal outputs; raw in `raw/` (ignored).
Rebuild: copy moveit2 2.12.4 `moveit_ros/moveit_servo` into `build_ws/src/moveit_servo`, `patch -p1`, then
`colcon build --packages-select moveit_servo --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF` in the trial image.
