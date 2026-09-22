# S3 fake OpenVR inputs

The unmodified existing harness obtains each trial's fake OpenVR input from these environment variables: `OPENVR_FAKE_VALID`, `OPENVR_FAKE_TRACKING_RESULT`, `OPENVR_FAKE_GRIP=true`, `OPENVR_FAKE_MOTION_Z=0.001`, and `OPENVR_FAKE_MOTION_MAX_STEPS=300`.

The production process's stderr (`W1_node.log`, `W2_node.log`, and `W3_node.log`) records the actual fake-module configuration. W0 deliberately has no teleop process. The complete launch commands are in `../commands.txt`.
