#!/usr/bin/env python3
"""F3 deployment-component patch for xrizer 0989a7f (applied on top of xrizer_extfilter.patch). The APP stays unmodified.
For OpenVR Background apps that never call WaitGetPoses/Submit, xrizer (a) never drives OpenXR frames, so the session
never reaches FOCUSED, and (b) locates every pose at the init-time display_time (results/F2_TIMESTAMP_REVIEW.md).
This patch keeps the initial temporary session's FrameWaiter/FrameStream and, on each GetDeviceToAbsoluteTrackingPose,
runs one empty frame (wait/begin/end with 0 layers), sets display_time to the predicted display time, and (v2) runs
the input frame-start update that WaitGetPoses would normally run (legacy action load + sync)."""
import sys
root = sys.argv[1]
def edit(path, old, new, count=1):
    p = f'{root}/{path}'; s = open(p).read()
    assert s.count(old) >= 1, (path, old[:70]); s = s.replace(old, new, count); open(p, 'w').write(s)
edit('src/openxr_data.rs', "    pub enabled_extensions: xr::ExtensionSet,\n\n    /// should only be externally accessed for testing",
     "    pub enabled_extensions: xr::ExtensionSet,\n    /// F3 patch: frame pump for Background apps (temporary session's waiter/stream)\n    pub bg_frames: std::sync::Mutex<Option<(xr::FrameWaiter, FrameStream)>>,\n\n    /// should only be externally accessed for testing")
edit('src/openxr_data.rs', """        let session_data = SessionReadGuard(RwLock::new(ManuallyDrop::new(
            SessionData::new(
                &instance,
                system_id,
                vr::ETrackingUniverseOrigin::Standing,
                None,
            )?
            .0,
        )));""", """        let (first_session, bg_waiter, bg_stream) = SessionData::new(
            &instance,
            system_id,
            vr::ETrackingUniverseOrigin::Standing,
            None,
        )?;
        let session_data = SessionReadGuard(RwLock::new(ManuallyDrop::new(first_session)));""")
edit('src/openxr_data.rs', "            enabled_extensions: exts,\n            input: injector.inject(),",
     "            enabled_extensions: exts,\n            bg_frames: std::sync::Mutex::new(Some((bg_waiter, bg_stream))),\n            input: injector.inject(),")
edit('src/openxr_data.rs', "    pub fn poll_events(&self) {", """    /// F3 patch: drive one empty frame on the temporary session (Background apps only call pose getters).
    pub fn pump_background_frame(&self) {
        self.poll_events();
        let mut guard = self.bg_frames.lock().unwrap();
        let Some((waiter, stream)) = guard.as_mut() else { return };
        {
            let data = self.session_data.get();
            if !matches!(data.state, xr::SessionState::READY | xr::SessionState::SYNCHRONIZED
                | xr::SessionState::VISIBLE | xr::SessionState::FOCUSED) { return; }
        }
        let Ok(fs) = waiter.wait() else { return };
        if let FrameStream::Vulkan(s) = stream {
            if s.begin().is_err() { return; }
            let _ = s.end(fs.predicted_display_time, xr::EnvironmentBlendMode::OPAQUE, &[]);
        } else { return; }
        self.display_time.set(fs.predicted_display_time);
        drop(guard);
        // v2: legacy input is loaded/synced only in frame_start_update (normally from WaitGetPoses)
        if let Some(input) = self.input.get() { input.frame_start_update(); }
    }

    pub fn poll_events(&self) {""")
edit('src/system.rs', """        pose_count: u32,
    ) {
        self.input""", """        pose_count: u32,
    ) {
        self.openxr.pump_background_frame(); // F3 patch
        self.input""")
print('patched')
# v3: xrizer sets up legacy actions only on the "real" session (created at the first Submit). A Background app never
# submits, so with XRIZER_F3_LEGACY_ON_TEMP=1 we allow legacy actions on the temporary session.
edit('src/input.rs', "                if !data.is_real_session() {\n                    debug!(",
     "                if !data.is_real_session() && std::env::var(\"XRIZER_F3_LEGACY_ON_TEMP\").as_deref() != Ok(\"1\") {\n                    debug!(")
print('patched v3')
