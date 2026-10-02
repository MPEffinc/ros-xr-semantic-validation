#!/usr/bin/env bash
# Setup probe (not a measured trial): which runtime levers change which evidence, as seen by the runtime-side
# collector and by the client itself.
R=/results; mkdir -p $R /tmp/xdg; export XDG_RUNTIME_DIR=/tmp/xdg HOME=/tmp
cd /tmp && gcc -O2 -o sa /f1/collector/sa_client.c -lopenxr_loader && gcc -O2 -I/opt/monado/include -o mc /f1/collector/mnd_collector.c -L/opt/monado/lib -lmonado && gcc -O2 -I/opt/monado/include -o ctl /f1/collector/mnd_ctl.c -L/opt/monado/lib -lmonado || exit 3
(sleep 40 | XRT_COMPOSITOR_NULL=1 P_OVERRIDE_ACTIVE_CONFIG=remote XRT_LOG=info /opt/monado/bin/monado-service > $R/service.log 2>&1 &)
sleep 3; T0=$(date +%s.%N); echo "{\"t0\":$T0}" > $R/t0.json
echo '{"duration": 22, "grip": [[1, 22]]}' > /tmp/sc.json; python3 /f1/harness/remote_feeder.py /tmp/sc.json $T0 $R/feeder.jsonl &
/tmp/mc 0.005 21 > $R/collector.jsonl &
/tmp/sa 20 sa_main > $R/sa_main.jsonl 2>$R/sa_main.err &
sleep 0.5; /tmp/sa 19 sa_other > $R/sa_other.jsonl 2>$R/sa_other.err &
ev(){ sleep $1; echo "{\"wall\":$(date +%s.%N),\"action\":\"$2 $3\",\"out\":$(/tmp/ctl $2 $3 | head -1)}" >> $R/actions.jsonl; }
( ev 4.5 io sa_main; ev 3 io sa_main; ev 3 focus sa_other; ev 3 focus sa_main; ev 2 block_inputs sa_main; ev 2 unblock sa_main ) 
wait
