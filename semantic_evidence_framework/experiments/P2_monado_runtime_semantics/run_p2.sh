#!/usr/bin/env bash
# One P2 run on the host Monado runtime (no container). Args: <run_dir> <variant>
# variant A: deadman held 3-8 s, input removed (monado-ctl -i) at 6 s, released at 8 s while removed, input restored at 10 s
# variant B: deadman held 3-14 s, input removed at 6 s, restored at 10 s (held throughout)
set -u; R=$1; V=$2; mkdir -p "$R"; P=$(cd "$(dirname "$0")" && pwd); BIN=${P2_CLIENT_BIN:?}
case $V in A) IV='[[3,8]]';; B) IV='[[3,14]]';; F) IV='[[3,8]]';; esac
(sleep 30 | XRT_COMPOSITOR_NULL=1 P_OVERRIDE_ACTIVE_CONFIG=remote XRT_LOG=info timeout 28 monado-service > "$R/service.log" 2>&1 &)
sleep 3
python3 "$P/remote_feeder.py" "$IV" 20 "$R/feeder.jsonl" & FP=$!
sleep 1
"$BIN" 18 > "$R/client.jsonl" 2> "$R/client.err" & CP=$!
T0=$(date +%s.%N); echo "{\"t0\":$T0,\"variant\":\"$V\"}" > "$R/run.json"
sleep 2; monado-ctl > "$R/ctl_list.txt" 2>&1
ID=$(grep 'p2_probe' "$R/ctl_list.txt" | grep -oE 'id: [0-9]+' | head -1 | grep -oE '[0-9]+'); echo "client_id=$ID" >> "$R/ctl_list.txt"
sleep 3   # t = 6 s after feeder start
monado-ctl > "$R/ctl_list_before_off.txt" 2>&1
if [ "$V" = F ]; then monado-ctl -f -1 >> "$R/ctl_actions.txt" 2>&1; else monado-ctl -i "$ID" >> "$R/ctl_actions.txt" 2>&1; fi; echo "off $(date +%s.%N)" >> "$R/ctl_actions.txt"
sleep 1; monado-ctl > "$R/ctl_list_during_off.txt" 2>&1
sleep 3   # t = 10 s
if [ "$V" = F ]; then monado-ctl -f "$ID" >> "$R/ctl_actions.txt" 2>&1; else monado-ctl -i "$ID" >> "$R/ctl_actions.txt" 2>&1; fi; echo "on $(date +%s.%N)" >> "$R/ctl_actions.txt"
wait $CP; kill $FP 2>/dev/null; pkill -f monado-service; sleep 1
