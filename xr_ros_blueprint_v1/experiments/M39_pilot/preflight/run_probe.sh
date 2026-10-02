#!/usr/bin/env bash
# Pre-flight B1-detection probe: runtime IO toggles (long, short, sub-tick), operator release, tracking loss.
R=/results; mkdir -p /tmp/xdg; export XDG_RUNTIME_DIR=/tmp/xdg HOME=/tmp
cd /tmp && gcc -O2 -I/opt/monado/include -o mc /m39/harness/mnd_collector.c -L/opt/monado/lib -lmonado && gcc -O2 -I/opt/monado/include -o sched /m39/harness/mnd_sched.c -L/opt/monado/lib -lmonado || exit 3
mkdir -p /tmp/xrizer/bin/linux64 && cp /src/xrizer/target/release/libxrizer.so /tmp/xrizer/bin/linux64/vrclient.so
mkdir -p $HOME/.config/openvr && echo '{"version":1,"runtime":["/tmp/xrizer"]}' > $HOME/.config/openvr/openvrpaths.vrpath
(sleep 45 | XRT_COMPOSITOR_NULL=1 P_OVERRIDE_ACTIVE_CONFIG=remote XRT_LOG=warn /opt/monado/bin/monado-service > $R/service.log 2>&1 &)
sleep 2; T0=$(python3 -c "import time;print(time.time()+4)")
echo '{"duration": 34, "grip": [[2.0, 18.0], [19.0, 34]], "u": [1,0,0], "trans": [[4.0, 30.0, 0.01]], "controller_inactive": [[24.0, 25.0]]}' > /tmp/sc.json
python3 /m39/harness/remote_feeder.py /tmp/sc.json $T0 $R/feeder.jsonl > /dev/null 2>&1 &
/tmp/mc 0.005 40 > $R/collector.jsonl &
XRIZER_F3_LEGACY_ON_TEMP=1 python3 /m39/preflight/probe_detect.py $R/probe.jsonl 36 > $R/probe.log 2>&1 &
pr=$!
# IO off/on pairs (relative to T0): 1.5 s, 0.2 s, 0.03 s (< one app tick), 1.5 s during release, x3 0.03 s
/tmp/sched python3.12 $T0 6.000 7.500 10.000 10.200 12.000 12.030 13.000 13.030 14.000 14.030 17.500 19.500 > $R/sched.jsonl 2>&1 &
wait $pr; echo "{\"t0\":$T0}" > $R/done.json
