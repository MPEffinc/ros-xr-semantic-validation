(function (global) {
    "use strict";

    function finiteNumber(value) {
        return Number.isFinite(value) ? value : null;
    }

    function vector(value, keys) {
        if (!value) return null;
        const result = {};
        for (const key of keys) result[key] = finiteNumber(value[key]);
        return result;
    }

    function transformSnapshot(transform) {
        if (!transform) return null;
        return {
            position: vector(transform.position, ["x", "y", "z"]),
            orientation: vector(transform.orientation, ["x", "y", "z", "w"]),
        };
    }

    class SemanticLogger {
        constructor(options = {}) {
            this.emitFunction = options.emit || (() => {});
            this.sampleIntervalMs = options.sampleIntervalMs || 200;
            this.lastSignature = null;
            this.lastPreliminarySignature = null;
            this.lastSampleMs = Number.NEGATIVE_INFINITY;
            this.eventSequence = 0;
        }

        _emit(event) {
            try {
                this.eventSequence += 1;
                this.emitFunction({
                    schema: "spes-webxr-semantic-v1",
                    semantic_event_sequence: this.eventSequence,
                    ...event,
                });
            } catch (error) {
                // Observation must never interrupt the control path.
                console.error("Semantic logger error:", error);
            }
        }

        mark(eventKind, details = {}) {
            this._emit({
                event_kind: eventKind,
                local_monotonic_ms: finiteNumber(performance.now()),
                ...details,
            });
        }

        _preliminarySignature(observation) {
            return JSON.stringify({
                is_vr_device: Boolean(observation.isVRDevice),
                input_source_count: observation.inputSourceCount,
                right_controller_input_source_present: Boolean(
                    observation.rightControllerInputSourcePresent
                ),
                controller_pose_exists: Boolean(observation.controllerPose),
                controller_emulated_position: observation.controllerPose
                    ? Boolean(observation.controllerPose.emulatedPosition)
                    : null,
                selected_source: observation.selectedSource,
                move: Boolean(observation.move),
                gripper: observation.gripper,
                websocket_connected: Boolean(observation.websocketConnected),
            });
        }

        shouldObserve(observation) {
            try {
                const preliminary = this._preliminarySignature(observation);
                return (
                    preliminary !== this.lastPreliminarySignature ||
                    performance.now() - this.lastSampleMs >= this.sampleIntervalMs
                );
            } catch (error) {
                console.error("Semantic observer scheduling error:", error);
                return false;
            }
        }

        observe(observation) {
            try {
                const now = performance.now();
                const controllerPose = observation.controllerPose;
                const viewerPose = observation.viewerPose;
                const viewerTransform =
                    viewerPose && viewerPose.views && viewerPose.views[0]
                        ? viewerPose.views[0].transform
                        : null;
                const state = {
                    xr_frame_time: finiteNumber(observation.xrFrameTime),
                    local_monotonic_ms: finiteNumber(now),
                    is_vr_device: Boolean(observation.isVRDevice),
                    input_source_count: observation.inputSourceCount,
                    right_controller_input_source_present: Boolean(
                        observation.rightControllerInputSourcePresent
                    ),
                    controller_pose_exists: Boolean(controllerPose),
                    controller_emulated_position: controllerPose
                        ? Boolean(controllerPose.emulatedPosition)
                        : null,
                    controller_pose: controllerPose
                        ? {
                              position: vector(controllerPose.position, ["x", "y", "z"]),
                              orientation: vector(controllerPose.orientation, ["x", "y", "z", "w"]),
                          }
                        : null,
                    viewer_pose_exists: Boolean(viewerTransform),
                    viewer_emulated_position: viewerPose
                        ? Boolean(viewerPose.emulatedPosition)
                        : null,
                    viewer_pose: transformSnapshot(viewerTransform),
                    selected_source: observation.selectedSource,
                    move: Boolean(observation.move),
                    gripper: observation.gripper,
                    websocket_connected: Boolean(observation.websocketConnected),
                    control_packet_index: observation.controlPacketIndex,
                };
                const signature = JSON.stringify({
                    is_vr_device: state.is_vr_device,
                    input_source_count: state.input_source_count,
                    right_controller_input_source_present:
                        state.right_controller_input_source_present,
                    controller_pose_exists: state.controller_pose_exists,
                    controller_emulated_position: state.controller_emulated_position,
                    viewer_pose_exists: state.viewer_pose_exists,
                    viewer_emulated_position: state.viewer_emulated_position,
                    selected_source: state.selected_source,
                    move: state.move,
                    gripper: state.gripper,
                    websocket_connected: state.websocket_connected,
                });
                const transition = signature !== this.lastSignature;
                const sampleDue = now - this.lastSampleMs >= this.sampleIntervalMs;
                if (transition || sampleDue) {
                    this._emit({
                        event_kind: transition ? "semantic_transition" : "semantic_sample",
                        ...state,
                    });
                    this.lastSampleMs = now;
                }
                this.lastSignature = signature;
                this.lastPreliminarySignature = this._preliminarySignature(observation);
            } catch (error) {
                // Observation must never interrupt the control path.
                console.error("Semantic observer error:", error);
            }
        }
    }

    global.SemanticLogger = SemanticLogger;
})(globalThis);
