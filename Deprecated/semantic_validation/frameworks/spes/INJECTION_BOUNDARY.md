# Spes replay injection boundary

- Relevant native source: WebXR `XRFrame.getPose`, input-source selection and viewer fallback
  in `teleop/index.html:264-355`.
- First decisions: controller-vs-viewer choice and browser `position && orientation` check;
  server `move` and jump policy are later decisions.
- Available replay point: WSS `pose` JSON accepted by production FastAPI `/ws`.
- Active logic: actual WSS handler, `Teleop.__update`, `move` gate, conversion, jump protection,
  anchors/recovery, and callback.
- Bypassed logic: WebXR runtime, source selection/fallback, browser pose check, raw source time
  and raw tracking semantics.

Classification: **`BOUNDARY_LIMITED_REPLAY`**. The synthetic suite proves only the WSS/server
boundary, never the browser native decision or actual Quest behavior.
