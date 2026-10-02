#!/usr/bin/env bash
# Print docker args exposing the host NVIDIA Vulkan user-space driver (no nvidia-container-runtime on this host).
V=580.173.02; L=/usr/lib/x86_64-linux-gnu; A=""
for d in /dev/nvidia0 /dev/nvidiactl /dev/nvidia-uvm /dev/nvidia-uvm-tools /dev/nvidia-modeset; do A="$A --device $d"; done
for f in $L/*nvidia*; do [ -f "$f" ] && A="$A -v $f:/opt/nvhost/$(basename $f):ro"; done
[ -d /usr/share/nvidia ] && A="$A -v /usr/share/nvidia:/usr/share/nvidia:ro"
echo "$A -e NVHOST_V=$V"
