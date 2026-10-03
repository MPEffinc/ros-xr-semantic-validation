#!/usr/bin/env bash
# M3_far trial (R25): runs the frozen M3_ordering/harness/trial_ord.sh unchanged except that the LATE injector is
# /m3f/harness/far_injector.py. The substitution is made on a /tmp copy; the frozen file is read-only.
sed 's#/m3o/harness/late_injector.py#/m3f/harness/far_injector.py#' /m3o/harness/trial_ord.sh > /tmp/trial_far_run.sh
grep -q far_injector /tmp/trial_far_run.sh || { mkdir -p /results; echo '{"setup":"injector_substitution_failed"}' > /results/setup.json; exit 30; }
exec bash /tmp/trial_far_run.sh
