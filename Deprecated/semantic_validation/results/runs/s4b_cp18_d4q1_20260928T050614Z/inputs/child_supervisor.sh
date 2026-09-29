#!/usr/bin/env bash
# Trial-only parent exit contract; no policy or ROS message decision.
wait_required_finished() {
  local child_pid=$1 child_label=$2 child_rc
  if wait "$child_pid"; then
    return 0
  else
    child_rc=$?
    echo "required child $child_label exited $child_rc" >&2
    return "$child_rc"
  fi
}
assert_required_running() {
  local child_pid=$1 child_label=$2 state
  state=$(ps -o stat= -p "$child_pid" 2>/dev/null) || state=''
  case "$state" in
    ''|Z*) echo "required child $child_label is not running: $state" >&2; return 17 ;;
    *) return 0 ;;
  esac
}
