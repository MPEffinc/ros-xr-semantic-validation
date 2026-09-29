# Legged injection boundary

The first inspected hand gate is `XRHand.isTracked` in `HandPub.OnHandUpdate`. Injecting
landmarks, PointCloud, TF, or ROS-TCP data after that point bypasses the gate and all native
hand semantics. Such an adapter would be `BOUNDARY_LIMITED_REPLAY`; none is created because the
control-producing downstream path remains unconfirmed.
