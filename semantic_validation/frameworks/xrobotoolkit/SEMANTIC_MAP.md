# XRoboToolkit semantic map

The wire design preserves `timestamp_ns` and integer status fields structurally, but controller
status is overwritten to `3` on the publisher path and the audited ARX control example does not
consume status or freshness. Since the external PicoXR service is unavailable, these are E1
wire/downstream findings only, not a native XR semantic mapping or positive control.
