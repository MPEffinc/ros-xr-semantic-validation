#!/usr/bin/env bash
# Capture packets inside a running container's network namespace, without host root.
# A sidecar container joins the target's netns (--net container:<target>) with NET_RAW/NET_ADMIN
# and runs tcpdump; the pcap is written to a host directory OUTSIDE Git (default: results/raw/).
#
# Usage: capture_flows.sh <target_container> <iface|any> <seconds> <out.pcap> [bpf filter]
# Docker on this host must be invoked through `sg docker -c` (see docs/00_asset_inventory.md).
set -euo pipefail
target="$1"; iface="$2"; secs="$3"; out="$4"; filter="${5:-}"
outdir="$(cd "$(dirname "$out")" && pwd)"; base="$(basename "$out")"
docker run --rm --net "container:${target}" --cap-add NET_RAW --cap-add NET_ADMIN \
  -v "${outdir}:/cap" crossflow-capture:local \
  timeout "${secs}" tcpdump -i "${iface}" -s 128 -U -w "/cap/${base}" ${filter} || true
ls -l "${out}"
