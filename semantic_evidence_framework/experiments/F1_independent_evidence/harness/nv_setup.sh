# source inside the container: make /opt/nvhost a Vulkan ICD
mkdir -p /tmp/nvlib && for f in /opt/nvhost/*; do ln -sf $f /tmp/nvlib/$(basename $f); b=$(basename $f .$NVHOST_V); [ "$b" != "$(basename $f)" ] && { [ -e /tmp/nvlib/$b.1 ] || ln -sf $f /tmp/nvlib/$b.1; [ -e /tmp/nvlib/$b.0 ] || ln -sf $f /tmp/nvlib/$b.0; }; done
printf '{"file_format_version":"1.0.1","ICD":{"library_path":"/tmp/nvlib/libGLX_nvidia.so.0","api_version":"1.4.312"}}' > /tmp/nvidia_icd.json
export LD_LIBRARY_PATH=/tmp/nvlib:${LD_LIBRARY_PATH:-} VK_ICD_FILENAMES=/tmp/nvidia_icd.json
