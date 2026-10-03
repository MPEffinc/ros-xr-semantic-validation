#!/usr/bin/env bash
# M17 trial (R28). Env: ARM (AP|TV), COND (NORMAL|FAKE_TARGET|REWRITE_STALE|WRONG_MAP), TRIAL. Command level, no robot.
# Processes: trusted source + robot state, app (scripted condition), one gate arm. 9 s run; window 5.0-6.0 s.
R=/results; mkdir -p $R; source /opt/ros/jazzy/setup.bash; source /m17b/install/local_setup.bash
export ROS_DOMAIN_ID=93 ROS_LOCALHOST_ONLY=1; END=9.0
export T0=$(python3 -c "import time;print(time.time()+3.0)")
echo "{\"setup\":\"ok\",\"t0\":$T0,\"arm\":\"$ARM\",\"cond\":\"$COND\",\"trial\":\"$TRIAL\",\"load\":\"$(cut -d' ' -f1-3 /proc/loadavg)\"}" > $R/setup.json
python3 /m17/harness/gate.py $ARM $R/gate.jsonl $END > $R/gate.log 2>&1 & g=$!
python3 /m17/harness/app.py $COND $R/truth.jsonl $END > $R/app.log 2>&1 & a=$!
python3 /m17/harness/source.py $R/source.jsonl $END > $R/source.log 2>&1 & s=$!
wait $s $a $g; echo "{\"done\":true}" > $R/done.json
