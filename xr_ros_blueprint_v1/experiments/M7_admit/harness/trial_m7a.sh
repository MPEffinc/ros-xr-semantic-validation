#!/usr/bin/env bash
# M7_admit trial (R24): runs the frozen M7_frame/harness/trial_m7.sh unchanged except that the bridge process is
# /m7a/harness/m7_bridge_admit.py (30 ms delay). The substitution is made on a /tmp copy; the frozen file is read-only.
sed 's#/m7/harness/m7_bridge.py#/m7a/harness/m7_bridge_admit.py#' /m7/harness/trial_m7.sh > /tmp/trial_m7a_run.sh
grep -q m7_bridge_admit /tmp/trial_m7a_run.sh || { mkdir -p /results; echo '{"setup":"bridge_substitution_failed"}' > /results/setup.json; exit 30; }
exec bash /tmp/trial_m7a_run.sh
