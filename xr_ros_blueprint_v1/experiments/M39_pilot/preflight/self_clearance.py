#!/usr/bin/env python3
"""Offline pre-flight: approximate self-collision clearance (min vertex distance between STL collision meshes of the
ACM-enabled link pairs) for a joint configuration, to explain/predict MoveIt Servo DECEL_FOR_COLLISION (threshold
self_collision_proximity_threshold = 0.01 m, unpadded). Vertex-to-vertex distance overestimates the true mesh distance.
Args: <urdf> <mesh_dir> <srdf> <q1..q6> [more configs as further 6-tuples]"""
import struct, sys, xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R
urdf, mesh_dir, srdf = sys.argv[1:4]; vals = [float(x) for x in sys.argv[4:]]
root = ET.parse(urdf).getroot()
def stl(p):
    b = open(p, 'rb').read()
    if b[:5] == b'solid' and b'facet' in b[:300]:
        v = [list(map(float, l.split()[1:4])) for l in b.decode(errors='ignore').splitlines() if l.strip().startswith('vertex')]
        return np.unique(np.array(v), axis=0)
    n = struct.unpack('<I', b[80:84])[0]; a = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
    return np.unique(a['v'].reshape(-1, 3).astype(float), axis=0)
links = {}
for l in root.findall('link'):
    c = l.find('collision')
    if c is None: continue
    g = c.find('geometry')[0]; o = c.find('origin'); sc = g.get('scale')
    T = np.eye(4)
    if o is not None:
        T[:3, :3] = R.from_euler('xyz', [float(x) for x in o.get('rpy', '0 0 0').split()]).as_matrix(); T[:3, 3] = [float(x) for x in o.get('xyz', '0 0 0').split()]
    pts = stl(mesh_dir + '/' + g.get('filename').split('/')[-1])
    if sc: pts = pts * np.array([float(x) for x in sc.split()])
    links[l.get('name')] = (T, pts)
joints = {j.find('child').get('link'): j for j in root.findall('joint')}
def chain_T(link, q):
    if link not in joints: return np.eye(4)
    j = joints[link]; o = j.find('origin'); T = np.eye(4)
    T[:3, :3] = R.from_euler('xyz', [float(x) for x in o.get('rpy', '0 0 0').split()]).as_matrix(); T[:3, 3] = [float(x) for x in o.get('xyz', '0 0 0').split()]
    Tj = np.eye(4); n = j.get('name')
    if n in q: Tj[:3, :3] = R.from_rotvec(np.array([float(x) for x in j.find('axis').get('xyz').split()]) * q[n]).as_matrix()
    return chain_T(j.find('parent').get('link'), q) @ T @ Tj
dis = set()
for d in ET.parse(srdf).getroot().findall('disable_collisions'): dis.add(frozenset((d.get('link1'), d.get('link2'))))
J = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint", "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
for k in range(0, len(vals), 6):
    q = dict(zip(J, vals[k:k + 6])); W = {}
    for n, (To, p) in links.items():
        T = chain_T(n, q) @ To; W[n] = p @ T[:3, :3].T + T[:3, 3]
    names = sorted(W); res = []
    for i, a in enumerate(names):
        ta = cKDTree(W[a])
        for b in names[i + 1:]:
            if frozenset((a, b)) in dis: continue
            dd, _ = ta.query(W[b], k=1); res.append((float(dd.min()), a, b))
    res.sort(); print(json_line := {"q": vals[k:k + 6], "closest": [(round(d * 1000, 1), a, b) for d, a, b in res[:4]]})
