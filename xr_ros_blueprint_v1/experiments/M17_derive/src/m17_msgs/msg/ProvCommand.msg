# App command with app-supplied provenance (all fields are chosen by the app process).
std_msgs/Header header
uint64 cmd_id
string src_session
uint64 src_seq
builtin_interfaces/Time src_time
bool valid
geometry_msgs/Point target
