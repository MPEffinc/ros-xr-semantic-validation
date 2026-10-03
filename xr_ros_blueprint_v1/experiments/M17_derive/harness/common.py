"""M17 shared constants (frozen mapping specification; the verifier reads it from here, never from the app)."""
import math
ANCHOR = (0.40, 0.00, 0.30)      # robot EE at engage (published by the trusted robot-state process)
K = 1.0                          # declared mapping: target = anchor + K * (hand - hand_ref)
TAU = 0.100                      # age limit (s)
TOL = 0.001                      # verifier target tolerance (m)
W0, W1 = 5.0, 6.0                # attack window (s after T0)
ENGAGE_T = 1.0                   # source grip goes true at this time (s after T0)
def hand(t):                     # synthetic hand motion (m): 0.05 m amplitude, 0.5 Hz on x; slow 0.02 m on y
    return (0.10 + 0.05 * math.sin(2 * math.pi * 0.5 * t), 0.02 * math.sin(2 * math.pi * 0.2 * t), 0.20)
def mapping(h, h_ref, anchor=ANCHOR, k=K): return tuple(a + k * (x - r) for a, x, r in zip(anchor, h, h_ref))
