R=/results; mkdir -p /tmp/xdg; export XDG_RUNTIME_DIR=/tmp/xdg HOME=/tmp
mkdir -p /tmp/xrizer/bin/linux64 && cp /src/xrizer/target/release/libxrizer.so /tmp/xrizer/bin/linux64/vrclient.so
mkdir -p $HOME/.config/openvr && echo '{"version":1,"runtime":["/tmp/xrizer"]}' > $HOME/.config/openvr/openvrpaths.vrpath
(sleep 30 | XRT_COMPOSITOR_NULL=1 P_OVERRIDE_ACTIVE_CONFIG=remote XRT_LOG=warn /opt/monado/bin/monado-service > $R/service.log 2>&1 &)
sleep 3; T0=$(date +%s.%N); echo '{"duration": 20, "grip": [[3, 20]], "motion_x": [[5, 9, 0.05]]}' > /tmp/sc.json
python3 /f3/harness/../../F1_independent_evidence/harness/remote_feeder.py /tmp/sc.json $T0 $R/feeder.jsonl 2>/dev/null &
sleep 0.5; python3 /f3/harness/openvr_probe.py > $R/probe.txt 2> $R/probe.err; wait
