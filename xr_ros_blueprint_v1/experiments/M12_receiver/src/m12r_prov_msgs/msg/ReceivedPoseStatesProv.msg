# M12_receiver B1 typed provenance schema: the receiver's original output message plus the provenance of the packet
# it was built from (same message, so payload and provenance cannot be mismatched).
teleop_bridge_msgs/ReceivedPoseStates state
bool neutral                         # true if the receiver substituted its neutral state (stale timeout / startup)
uint64 rx_count                      # receiver-side count of the packet the state came from (0 = none yet)
builtin_interfaces/Time rx_stamp     # receiver clock at receipt of that packet (packet receipt, not sensing)
bool src_seq_valid                   # producer supplied 'seq' and 'session'
int64 src_seq
string src_session
bool src_time_valid                  # producer supplied 'timestamp' (Unity Time.time, producer clock; not comparable to rx_stamp)
float64 src_time
