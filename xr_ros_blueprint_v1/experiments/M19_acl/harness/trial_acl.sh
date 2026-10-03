#!/usr/bin/env bash
# M19 trial (R27). Env: DEPLOY (D_OPEN|D_RESTRICT), CHECK (APPROVED|APP_DIRECT|MUX_DIRECT), TRIAL.
# Every ROS process runs with ROS_SECURITY_ENABLE=true, ROS_SECURITY_STRATEGY=Enforce, its own enclave and its own uid:
#   robot_state_publisher + controller_manager + JTC + broadcaster (mock hardware)  /m19/controller  uid 2003
#   topic_tools mux  /m19/app_cmd -> controller topic        /m19/mux         uid 2002
#   observer                                                 /m19/observer    uid 2004
#   payload publisher: APPROVED -> app on /m19/app_cmd; APP_DIRECT -> app on the controller topic (/m19/app, uid 2001);
#                      MUX_DIRECT -> same payload on the controller topic under /m19/mux (uid 2002) = positive control.
# Probes before the payload: (1) a node with security enabled but no enclave must fail under Enforce; (2) uid 2001
# must not read the mux / controller private keys or the CA private keys.
set -o pipefail; R=/results; mkdir -p $R; source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=0 ROS_LOCALHOST_ONLY=1   # sros2 permissions are generated for domain 0; container has --network none RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_SECURITY_KEYSTORE=/keys/$DEPLOY/ks ROS_SECURITY_ENABLE=true ROS_SECURITY_STRATEGY=Enforce
log(){ echo "{\"wall\":$(date +%s.%N),\"ev\":\"$1\"$2}" >> $R/harness.jsonl; }
pids=(); cleanup(){ for p in "${pids[@]}"; do kill -INT -- "-$p" 2>/dev/null; done; sleep 1; for p in "${pids[@]}"; do kill -KILL -- "-$p" 2>/dev/null; done; }
trap cleanup EXIT
as(){ local u=$1 e=$2; shift 2; mkdir -p /tmp/h$u && chown $u /tmp/h$u; setpriv --reuid=$u --regid=$u --clear-groups env HOME=/tmp/h$u ROS_LOG_DIR=/tmp/h$u/log ROS_SECURITY_ENCLAVE_OVERRIDE=/m19/$e "$@"; }
log start ",\"deploy\":\"$DEPLOY\",\"check\":\"$CHECK\",\"trial\":\"$TRIAL\",\"rmw\":\"$RMW_IMPLEMENTATION\",\"strategy\":\"$ROS_SECURITY_STRATEGY\""
# probe 1: enforcement (no enclave for this name -> node creation must fail)
timeout 20 setpriv --reuid=2005 --regid=2005 --clear-groups env HOME=/tmp ROS_LOG_DIR=/tmp/p5 ROS_SECURITY_ENCLAVE_OVERRIDE=/m19/none python3 -c "import rclpy; rclpy.init(); rclpy.create_node('probe'); print('NODE_CREATED')" > $R/probe_enforce.log 2>&1; rc=$?
log probe_enforce ",\"rc\":$rc,\"node_created\":$(grep -q NODE_CREATED $R/probe_enforce.log && echo true || echo false)"
# probe 2: key readability by the app uid
for f in enclaves/m19/mux/key.pem enclaves/m19/controller/key.pem private/identity_ca.key.pem private/permissions_ca.key.pem private/ca.key.pem; do
  if [ -e $ROS_SECURITY_KEYSTORE/$f ] || [ -L $ROS_SECURITY_KEYSTORE/$f ]; then
    setpriv --reuid=2001 --regid=2001 --clear-groups head -c1 $ROS_SECURITY_KEYSTORE/$f > /dev/null 2>&1 && r=readable || r=denied
    log key_access ",\"file\":\"$f\",\"by_uid\":2001,\"result\":\"$r\""; fi; done
log app_permissions ",\"sha16\":\"$(cat /keys/$DEPLOY/app_permissions.sha16)\""
cd /tmp
as 2003 controller setsid ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$(cat /m19/config/mock_ur.urdf)" > $R/rsp.log 2>&1 & pids+=($!)
as 2003 controller setsid ros2 run controller_manager ros2_control_node --ros-args --params-file /m19/config/controllers.yaml > $R/controller.log 2>&1 & pids+=($!)
sleep 3
as 2003 controller timeout 45 ros2 run controller_manager spawner joint_state_broadcaster ur5_arm_controller --controller-manager-timeout 30 > $R/spawner.log 2>&1 || { log setup_failed ",\"step\":\"spawner\""; echo '{"setup":"spawner_failed"}' > $R/setup.json; exit 21; }
as 2002 mux setsid ros2 run topic_tools mux /ur5_arm_controller/joint_trajectory /m19/app_cmd --ros-args -r __node:=m19_mux > $R/mux.log 2>&1 & pids+=($!)
as 2004 observer setsid python3 /m19/harness/observer_acl.py $R/observer.jsonl 14 > $R/observer.log 2>&1 & pids+=($!)
sleep 4; log payload_start
case $CHECK in
  APPROVED)   as 2001 app python3 /m19/harness/pub_once.py /m19/app_cmd $R/pub.jsonl m19_app > $R/pub.log 2>&1 ;;
  APP_DIRECT) as 2001 app python3 /m19/harness/pub_once.py /ur5_arm_controller/joint_trajectory $R/pub.jsonl m19_app > $R/pub.log 2>&1 ;;
  MUX_DIRECT) as 2002 mux python3 /m19/harness/pub_once.py /ur5_arm_controller/joint_trajectory $R/pub.jsonl m19_mux_direct > $R/pub.log 2>&1 ;;
esac
log payload_done ",\"rc\":$?"
sleep 4; echo '{"setup":"ok"}' > $R/setup.json; log end
