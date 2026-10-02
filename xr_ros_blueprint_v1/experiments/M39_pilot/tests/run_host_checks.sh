#!/usr/bin/env bash
# TEST-ONLY host checks inside the trial image (ROS Jazzy), no Gazebo/Servo/runtime: fake world + recorded/synthetic input.
R=/results; source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=88 ROS_LOCALHOST_ONLY=1 M39_HARNESS=/m39/harness
python3 /m39/tests/make_traces.py /m39/raw/preflight/probe_detect $R/traces || exit 3
F3=/f3raw/B0_r1; F3T0=$(python3 -c "import json;print(json.load(open('$F3/setup.json'))['t0'])")
EE="0.45 0.01 0.31 0.0499 0.7413 0.0526 0.6672"   # (0.45,0.01,0.31), H*Ry(0.1)-like, nontrivial dp and C
case_b1(){ local name=$1; mkdir -p $R/$name; rm -f /tmp/ev.fifo; mkfifo /tmp/ev.fifo
  export P1_T0_NS=$(( $(date +%s%N) + 4000000000 ))
  M39_FAKE_EE="$EE" python3 /m39/tests/fake_world.py $R/$name/world.jsonl 17 & w=$!
  python3 /m39/tests/replay_fifo.py $R/traces/${name#B1_}_collector.jsonl $(cat $R/traces/${name#B1_}_src_t0) /tmp/ev.fifo &
  PYTHONPATH=/m39/tests/fake_openvr:$PYTHONPATH M39_FAKE_TRACE=$R/traces/${name#B1_}_trace.jsonl M39_ARM_LOG=$R/$name/arm.jsonl M39_EV_FIFO=/tmp/ev.fifo \
    timeout 21 python3 /m39/arms/quest_teleop_b1.py > $R/$name/app.log 2>&1
  wait $w; echo $P1_T0_NS > $R/$name/t0_ns; }
case_c1(){ local name=$1; shift; mkdir -p $R/$name; rm -f /tmp/ev.fifo; mkfifo /tmp/ev.fifo
  export P1_T0_NS=$(( $(date +%s%N) + 4000000000 ))
  M39_FAKE_EE="$EE" python3 /m39/tests/fake_world.py $R/$name/world.jsonl 17 & w=$!
  python3 /m39/tests/replay_fifo.py $F3/collector.jsonl $F3T0 /tmp/ev.fifo &
  timeout 21 python3 /m39/arms/c1_transition.py $R/$name/arm.jsonl /tmp/ev.fifo 16.5 > $R/$name/c1.log 2>&1 & c=$!
  python3 /m39/tests/replay_cmds.py $F3/observer.jsonl $F3T0 "$@"
  wait $c; wait $w; echo $P1_T0_NS > $R/$name/t0_ns; }
case_b1 B1_T1; case_b1 B1_T2; case_b1 B1_T3
case_c1 C1_F3; case_c1 C1_SIL 5.0 5.2
python3 /m39/tests/check_rebase_math.py > $R/rebase_math.json
python3 /m39/tests/check_results.py $R > $R/summary.json; cat $R/summary.json
