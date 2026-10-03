# M7: a pose expressed in a (possibly moving) frame, with the time at which that representation is valid.
std_msgs/Header header                  # transport header: header.stamp may be re-stamped by republishers
builtin_interfaces/Time represented_at  # time at which 'pose' is expressed in 'represented_frame' (set once, at creation)
string represented_frame
geometry_msgs/Pose pose
uint64 seq
