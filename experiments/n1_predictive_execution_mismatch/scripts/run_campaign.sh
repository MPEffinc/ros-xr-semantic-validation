#!/usr/bin/env bash
# Formal N1 campaign (frozen order, configs/protocol.yaml). Run on the host; drives the n1sim container.
set -u
B=$(cd "$(dirname "$0")/.." && pwd); OUT=/results/raw/formal; mkdir -p "$B/results/raw/formal"
H="1.57 -1.2 1.6 -1.97 -1.57 0"; PH='[[0,3,[0.08,0,0]],[3,4,[0,0,0]],[4,9,[-0.08,0,0]],[9,10,[0,0,0]]]'
declare -A C=([N0]="" [A]="--delay_ms 150" [C]="--filter 1" [D]="--obstacle 1 --box_rel 0.40 0 0" [F]="--sa 1" \
  [AC]="--delay_ms 150 --filter 1" [AD]="--delay_ms 150 --obstacle 1 --box_rel 0.40 0 0" \
  [CDF]="--filter 1 --obstacle 1 --box_rel 0.40 0 0 --sa 1" [ACDF]="--delay_ms 150 --filter 1 --obstacle 1 --box_rel 0.40 0 0 --sa 1")
ORDER="N0 A C D F AC AD CDF ACDF"
trial(){ sg docker -c "docker exec n1sim bash -lc 'source /opt/ros/jazzy/setup.bash; source /ws/install/setup.bash; timeout 150 python3 /scripts/n1_pipeline.py --out $OUT/$1_s$2.jsonl --home $H --t_run 10 --phases \"$PH\" --seed $2 $3'" >"$B/results/raw/formal/$1_s$2.stdout" 2>&1; echo "$(date -u +%FT%TZ) $1 s$2 rc=$?"; }
for s in 1 2 3 4 5; do for c in $ORDER; do trial "$c" "$s" "${C[$c]}"; done; done
sg docker -c "docker exec n1sim bash -lc 'bash /scripts/servo_swap.sh \"{\\\"use_smoothing\\\": true}\" $OUT/servo_swap_E.log'"
for s in 1 2 3 4 5; do trial E "$s" ""; done
sg docker -c "docker exec n1sim bash -lc 'bash /scripts/servo_swap.sh \"{}\" $OUT/servo_restore.log'"
echo CAMPAIGN_DONE
