"""M7 scripted frame 'moving_ref' relative to base_link, as a pure function of sim time (seconds).
STATIC: identity offset (0, 0, 0). DYNAMIC: translation along base y, y(t) = A sin(2 pi f (t - t_start)) for t >= t_start
(A = 0.05 m, f = 0.5 Hz, peak speed 0.157 m/s), x = z = 0, no rotation. The ground truth uses this function directly,
never tf."""
import math
A, F = 0.05, 0.5
def offset(t, dynamic, t_start):
    if not dynamic or t is None or t < t_start: return (0.0, 0.0, 0.0)
    return (0.0, A * math.sin(2 * math.pi * F * (t - t_start)), 0.0)
