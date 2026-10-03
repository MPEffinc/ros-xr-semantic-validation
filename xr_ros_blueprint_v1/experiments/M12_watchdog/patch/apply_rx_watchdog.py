#!/usr/bin/env python3
"""M12_watchdog: minimal patch to Monado 045931d drivers/remote (applied inside the image build).
- r_hub: record the receive time (CLOCK_MONOTONIC via os_monotonic_get_ns) and a receive counter of every packet
  (the packet-receipt time; NOT a sensor observation time; the remote protocol carries no source time).
- S1 receive watchdog (env M12_RX_WATCHDOG_MS > 0): if no packet was received for longer than the timeout, the
  controllers are reported exactly as when the packet's 'active' flag is false (pose relation flags 0, inputs inactive).
- S2 receive evidence (env M12_RX_EVIDENCE=<path>): after each packet, write "<rx_ns> <rx_count>\\n" to that file
  (overwrite at offset 0), for a separate checker. No effect on poses.
With neither variable set, behaviour is identical to the original driver."""
import sys
root = sys.argv[1] + "/src/xrt/drivers/remote/"
def edit(f, old, new):
    p = root + f; s = open(p).read(); assert old in s, (f, old); open(p, "w").write(s.replace(old, new, 1))
edit("r_internal.h", "\t//! The latest data received.\n\tstruct r_remote_data latest;",
     "\t//! The latest data received.\n\tstruct r_remote_data latest;\n\n\t//! M12: receive time (monotonic ns) and count of the latest packet.\n\tuint64_t m12_rx_ns;\n\tuint64_t m12_rx_count;")
edit("r_hub.c", "\t\t\tr->latest = data;\n",
     """\t\t\tr->latest = data;
\t\t\tr->m12_rx_ns = os_monotonic_get_ns(); // M12: packet receipt time
\t\t\tr->m12_rx_count++;
\t\t\t{
\t\t\t\tstatic const char *m12_ev = NULL;
\t\t\t\tstatic int m12_init = 0;
\t\t\t\tif (!m12_init) { m12_ev = getenv("M12_RX_EVIDENCE"); m12_init = 1; }
\t\t\t\tif (m12_ev != NULL) {
\t\t\t\t\tFILE *f = fopen(m12_ev, "r+");
\t\t\t\t\tif (f == NULL) { f = fopen(m12_ev, "w"); }
\t\t\t\t\tif (f != NULL) { fprintf(f, "%llu %llu\\n", (unsigned long long)r->m12_rx_ns, (unsigned long long)r->m12_rx_count); fclose(f); }
\t\t\t\t}
\t\t\t}
""")
edit("r_hub.c", "#include", "#include <stdio.h>\n#include <stdlib.h>\n#include \"os/os_time.h\"\n#include", )
helper = """
// M12: receive watchdog (S1). Returns true if the source is considered silent.
static bool
m12_rx_stale(struct r_hub *r)
{
	static int init = 0;
	static uint64_t timeout_ns = 0;
	if (!init) {
		const char *e = getenv("M12_RX_WATCHDOG_MS");
		timeout_ns = (e != NULL) ? (uint64_t)(atof(e) * 1e6) : 0;
		init = 1;
	}
	if (timeout_ns == 0) {
		return false;
	}
	return (os_monotonic_get_ns() - r->m12_rx_ns) > timeout_ns;
}
"""
edit("r_device.c", "static xrt_result_t\nr_device_update_inputs(", helper + "\nstatic xrt_result_t\nr_device_update_inputs(")
edit("r_device.c", "\t// TODO: refactor those loops into one\n\tif (!latest->active) {", "\t// TODO: refactor those loops into one\n\tif (!latest->active || m12_rx_stale(r)) {")
edit("r_device.c", "\tif (latest->active) {\n\t\tout_relation->relation_flags", "\tif (latest->active && !m12_rx_stale(r)) {\n\t\tout_relation->relation_flags")
edit("r_device.c", "#include", "#include <stdlib.h>\n#include \"os/os_time.h\"\n#include")
print("patched")
