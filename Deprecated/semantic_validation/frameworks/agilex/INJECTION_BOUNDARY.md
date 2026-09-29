# AgileX injection boundary

Any injectable point begins after `OculusReader.process_data` has decoded an APK logcat record.
It therefore bypasses the opaque native XR API, source identity selection, tracking decision and
time/session contract. No adapter is created; any later host/ROS replay would be
`BOUNDARY_LIMITED_REPLAY` only.
