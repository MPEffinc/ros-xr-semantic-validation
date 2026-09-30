#!/usr/bin/env python3
"""Parse a classic libpcap file (no third-party deps) into a per-packet CSV.

Columns: ts (s, float), wire_len, cap_len, src, dst, proto (udp/tcp/other), sport, dport, flow (5-tuple key
with endpoints sorted), dir (0 = lower endpoint -> higher, 1 = reverse).
Supports link types EN10MB (1) and LINUX_SLL (113) / SLL2 (276) as produced by `tcpdump -i any`.

Usage: preprocess_pcap.py in.pcap out.csv
"""
import csv, socket, struct, sys

def packets(path):
    with open(path, 'rb') as f:
        gh = f.read(24)
        magic = struct.unpack('<I', gh[:4])[0]
        if magic in (0xa1b2c3d4, 0xa1b23c4d): end = '<'
        elif magic in (0xd4c3b2a1, 0x4d3cb2a1): end = '>'
        else: raise ValueError('not a classic pcap file')
        nano = magic in (0xa1b23c4d, 0x4d3cb2a1)
        linktype = struct.unpack(end + 'I', gh[20:24])[0]
        while True:
            h = f.read(16)
            if len(h) < 16: return
            s, us, caplen, wirelen = struct.unpack(end + 'IIII', h)
            data = f.read(caplen)
            yield s + us * (1e-9 if nano else 1e-6), wirelen, caplen, linktype, data

def l3(linktype, d):
    if linktype == 1:            # Ethernet
        et = struct.unpack('!H', d[12:14])[0]; off = 14
        if et == 0x8100: et = struct.unpack('!H', d[16:18])[0]; off = 18
    elif linktype == 113:        # Linux cooked v1
        et = struct.unpack('!H', d[14:16])[0]; off = 16
    elif linktype == 276:        # Linux cooked v2
        et = struct.unpack('!H', d[0:2])[0]; off = 20
    else:
        return None
    return (et, d[off:]) if et == 0x0800 else None

def main(inp, out):
    n = 0
    with open(out, 'w', newline='') as fo:
        w = csv.writer(fo)
        w.writerow(['ts', 'wire_len', 'cap_len', 'src', 'dst', 'proto', 'sport', 'dport', 'flow', 'dir'])
        for ts, wl, cl, lt, d in packets(inp):
            r = l3(lt, d)
            if not r: continue
            _, ip = r
            ihl = (ip[0] & 0x0f) * 4; pr = ip[9]
            src = socket.inet_ntoa(ip[12:16]); dst = socket.inet_ntoa(ip[16:20])
            sp = dp = 0; proto = 'other'
            if pr in (6, 17) and len(ip) >= ihl + 4:
                sp, dp = struct.unpack('!HH', ip[ihl:ihl + 4]); proto = 'tcp' if pr == 6 else 'udp'
            a, b = (src, sp), (dst, dp)
            lo, hi = sorted([a, b])
            flow = f'{proto}|{lo[0]}:{lo[1]}|{hi[0]}:{hi[1]}'
            w.writerow([f'{ts:.9f}', wl, cl, src, dst, proto, sp, dp, flow, 0 if a == lo else 1]); n += 1
    print(f'{n} IPv4 packets -> {out}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
