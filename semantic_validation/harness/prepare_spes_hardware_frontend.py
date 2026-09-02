#!/usr/bin/env python3

"""Generate an instrumented Spes frontend without touching the upstream clone."""

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


VALIDATION_ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = VALIDATION_ROOT / "targets" / "spes_teleop"
SOURCE_FRONTEND = TARGET_ROOT / "teleop"
LOGGER_SOURCE = VALIDATION_ROOT / "instrumentation" / "semantic-logger.js"
OPERATOR_SOURCE = VALIDATION_ROOT / "instrumentation" / "quest-operator.js"
DEFAULT_OUTPUT = VALIDATION_ROOT / "instrumented" / "spes_frontend"
EXPECTED_COMMIT = "c5d808155a87b584d6147a5943d4b87c34c92db0"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one source anchor, found {count}")
    return source.replace(old, new, 1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def instrument(html: str) -> str:
    operator_version = hashlib.sha256(OPERATOR_SOURCE.read_bytes()).hexdigest()[:16]
    html = replace_once(
        html,
        '<button class="button" id="start-button">Start</button>',
        '<button class="button" id="start-button">START WEBXR</button>',
        "Quest start button label",
    )
    html = replace_once(
        html,
        '    <script src="/assets/teleop-ui.js"></script>\n',
        '    <script src="/assets/teleop-ui.js"></script>\n'
        '    <script src="/assets/semantic-logger.js"></script>\n'
        f'    <script src="/assets/quest-operator.js?v={operator_version}"></script>\n',
        "semantic logger script",
    )
    html = replace_once(
        html,
        "        let socket;\n        let isConnected = false;\n",
        """        let socket;
        let isConnected = false;
        let controlPacketIndex = 0;
        const semanticLogger = new SemanticLogger({
            sampleIntervalMs: 200,
            emit: (event) => {
                const serialized = JSON.stringify(event);
                console.log('SEMANTIC_DEBUG ' + serialized);
                if (isConnected && socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({ type: 'log', data: serialized }));
                }
            }
        });
        const questOperator = new SpesQuestExperimentOperator();
""",
        "websocket observer state",
    )
    html = replace_once(
        html,
        """                teleopUI.updateServerDiagnostics(serverStats);
            };

            socket.onclose = () => {
""",
        """                teleopUI.updateServerDiagnostics(serverStats);
                semanticLogger.mark('websocket_open', { websocket_connected: true });
                questOperator.onProductionWebSocket('open');
            };

            socket.onclose = () => {
""",
        "websocket open marker",
    )
    html = replace_once(
        html,
        """                teleopUI.updateServerDiagnostics(serverStats);

                // Attempt to reconnect after 3 seconds
""",
        """                teleopUI.updateServerDiagnostics(serverStats);
                semanticLogger.mark('websocket_close', { websocket_connected: false });
                questOperator.onProductionWebSocket('close');

                // Attempt to reconnect after 3 seconds
""",
        "websocket close marker",
    )
    html = replace_once(
        html,
        """                serverStats.connection = 'Error: ' + error.message;
                teleopUI.updateServerDiagnostics(serverStats);
            };
""",
        """                serverStats.connection = 'Error: ' + error.message;
                teleopUI.updateServerDiagnostics(serverStats);
                semanticLogger.mark('websocket_error', { websocket_connected: false });
                questOperator.onProductionWebSocket('error', { message: error.message || null });
            };
""",
        "websocket error marker",
    )
    html = replace_once(
        html,
        """                socket.send(JSON.stringify({
                    type: 'pose',
                    data: pose
                }));
""",
        """                socket.send(JSON.stringify({
                    type: 'pose',
                    data: pose
                }));
                controlPacketIndex += 1;
""",
        "control packet counter",
    )
    html = replace_once(
        html,
        """        function getPoseFromInputSource(session, frame, referenceSpace) {
""",
        """        function hasRightControllerInputSource(session) {
            return Array.from(session.inputSources).some(
                (inputSource) => inputSource.handedness === 'right' &&
                    inputSource.targetRayMode === 'tracked-pointer'
            );
        }

        function getPoseFromInputSource(session, frame, referenceSpace) {
""",
        "right input source observer helper",
    )
    html = replace_once(
        html,
        """                        return {
                            position: pose.transform.position,
                            orientation: pose.transform.orientation
                        };
""",
        """                        return {
                            position: pose.transform.position,
                            orientation: pose.transform.orientation,
                            emulatedPosition: pose.emulatedPosition === true
                        };
""",
        "controller emulatedPosition observation",
    )
    html = replace_once(
        html,
        """                }).then((session) => {
                    teleopUI.addEventListener('exit', () => {
""",
        """                }).then((session) => {
                    questOperator.onSessionStarted(session);
                    teleopUI.addEventListener('exit', () => {
""",
        "operator session start",
    )
    html = replace_once(
        html,
        """                    session.addEventListener('end', () => {
                        appDom.style.display = 'none';
""",
        """                    session.addEventListener('end', () => {
                        semanticLogger.mark('xr_session_end', {
                            visibility_state: session.visibilityState || null
                        });
                        questOperator.onSessionEnded();
                        appDom.style.display = 'none';
""",
        "session end marker",
    )
    html = replace_once(
        html,
        """                    session.addEventListener('inputsourceschange', () => {
                        isVRDevice = detectDeviceType(session);
                        setMessage(isVRDevice ? 'VR controllers detected' : 'Using device pose');
                    });
""",
        """                    session.addEventListener('inputsourceschange', () => {
                        isVRDevice = detectDeviceType(session);
                        semanticLogger.mark('inputsourceschange', {
                            is_vr_device: isVRDevice,
                            input_source_count: session.inputSources.length,
                            right_controller_input_source_present: hasRightControllerInputSource(session)
                        });
                        questOperator.onInputSourcesChange({
                            is_vr_device: isVRDevice,
                            input_source_count: session.inputSources.length,
                            right_controller_input_source_present: hasRightControllerInputSource(session)
                        });
                        setMessage(isVRDevice ? 'VR controllers detected' : 'Using device pose');
                    });

                    session.addEventListener('visibilitychange', () => {
                        semanticLogger.mark('xr_visibilitychange', {
                            visibility_state: session.visibilityState || null
                        });
                    });
""",
        "input source and visibility markers",
    )
    html = replace_once(
        html,
        """                            let position, orientation;

                            if (isVRDevice) {
""",
        """                            let position, orientation;
                            let selectedSource = 'NONE';
                            let controllerPoseForLog = null;
                            let viewerPoseForLog = null;
                            const inputSourceCount = session.inputSources.length;
                            const rightControllerInputSourcePresent = hasRightControllerInputSource(session);

                            if (isVRDevice) {
""",
        "frame observer variables",
    )
    html = replace_once(
        html,
        """                                const controllerPose = getPoseFromInputSource(session, frame, xrReferenceSpace);
                                if (controllerPose) {
                                    position = controllerPose.position;
                                    orientation = controllerPose.orientation;
                                } else {
                                    const viewerPose = frame.getViewerPose(xrReferenceSpace);
                                    if (viewerPose && viewerPose.views[0]) {
                                        position = viewerPose.views[0].transform.position;
                                        orientation = viewerPose.views[0].transform.orientation;
                                    }
                                }
                            } else {
                                const viewerPose = frame.getViewerPose(xrReferenceSpace);
                                if (viewerPose && viewerPose.views[0]) {
                                    position = viewerPose.views[0].transform.position;
                                    orientation = viewerPose.views[0].transform.orientation;
                                }
                            }

                            if (position && orientation) {
""",
        """                                const controllerPose = getPoseFromInputSource(session, frame, xrReferenceSpace);
                                controllerPoseForLog = controllerPose;
                                if (controllerPose) {
                                    selectedSource = 'CONTROLLER';
                                    position = controllerPose.position;
                                    orientation = controllerPose.orientation;
                                } else {
                                    const viewerPose = frame.getViewerPose(xrReferenceSpace);
                                    viewerPoseForLog = viewerPose;
                                    if (viewerPose && viewerPose.views[0]) {
                                        selectedSource = 'VIEWER_FALLBACK';
                                        position = viewerPose.views[0].transform.position;
                                        orientation = viewerPose.views[0].transform.orientation;
                                    }
                                }
                            } else {
                                const viewerPose = frame.getViewerPose(xrReferenceSpace);
                                viewerPoseForLog = viewerPose;
                                if (viewerPose && viewerPose.views[0]) {
                                    selectedSource = 'VIEWER_NON_VR';
                                    position = viewerPose.views[0].transform.position;
                                    orientation = viewerPose.views[0].transform.orientation;
                                }
                            }

                            const teleopFrontEnd = (isVRDevice) ? teleopJoystick : teleopUI;
                            const semanticObservation = {
                                xrFrameTime: time,
                                isVRDevice: isVRDevice,
                                inputSourceCount: inputSourceCount,
                                rightControllerInputSourcePresent: rightControllerInputSourcePresent,
                                controllerPose: controllerPoseForLog,
                                viewerPose: viewerPoseForLog,
                                selectedSource: selectedSource,
                                move: teleopFrontEnd.isMotionEnabled(),
                                gripper: teleopFrontEnd.isGripperEngaged() ? 'close' : 'open',
                                websocketConnected: isConnected && socket.readyState === WebSocket.OPEN,
                                controlPacketIndex: controlPacketIndex,
                                viewerPoseSampled: false
                            };
                            const observeThisFrame = semanticLogger.shouldObserve(semanticObservation);
                            // The non-selected viewer path is sampled only when an event/sample log is due.
                            if (observeThisFrame && viewerPoseForLog === null) {
                                viewerPoseForLog = frame.getViewerPose(xrReferenceSpace);
                                semanticObservation.viewerPose = viewerPoseForLog;
                            }
                            semanticObservation.viewerPoseSampled = observeThisFrame || controllerPoseForLog === null;

                            if (position && orientation) {
""",
        "source selection observations",
    )
    html = replace_once(
        html,
        """                                    const teleopFrontEnd = (isVRDevice) ? teleopJoystick : teleopUI;
                                    lastSendTime = time;
""",
        """                                    lastSendTime = time;
""",
        "frontend selection reuse",
    )
    html = replace_once(
        html,
        """                    session.updateRenderState({
                        baseLayer: new XRWebGLLayer(session, gl, {
                            antialias: false,
                            depth: false,
                            stencil: false,
                            alpha: false,
                            multiview: false
                        })
                    });

                    session.requestReferenceSpace('local-floor').then((referenceSpace) => {
""",
        """                    session.updateRenderState({
                        baseLayer: new XRWebGLLayer(session, gl, {
                            antialias: false,
                            depth: false,
                            stencil: false,
                            alpha: false,
                            multiview: false
                        })
                    });
                    questOperator.attachXRRenderer(gl, session);

                    session.requestReferenceSpace('local-floor').then((referenceSpace) => {
""",
        "in-XR HUD renderer attachment",
    )
    html = replace_once(
        html,
        """                            } else {
                                setMessage('No pose available');
                            }
                            session.requestAnimationFrame(onXRFrame);
""",
        """                            } else {
                                setMessage('No pose available');
                            }
                            if (observeThisFrame) {
                                semanticObservation.controlPacketIndex = controlPacketIndex;
                                semanticLogger.observe(semanticObservation);
                            }
                            semanticObservation.controlPacketIndex = controlPacketIndex;
                            questOperator.onFrame(semanticObservation);
                            questOperator.renderXRFrame(frame, xrReferenceSpace);
                            session.requestAnimationFrame(onXRFrame);
""",
        "semantic frame observation",
    )
    return html


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    commit = subprocess.run(
        ["git", "-C", str(TARGET_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if commit != EXPECTED_COMMIT:
        raise RuntimeError(f"Spes target drift: expected {EXPECTED_COMMIT}, found {commit}")
    status = subprocess.run(
        ["git", "-C", str(TARGET_ROOT), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise RuntimeError("Spes upstream checkout is not clean; refusing to generate instrumentation")

    output = args.output.resolve()
    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    source_index = SOURCE_FRONTEND / "index.html"
    generated_index = output / "index.html"
    generated_index.write_text(instrument(source_index.read_text(encoding="utf-8")), encoding="utf-8")
    shutil.copy2(SOURCE_FRONTEND / "assets" / "teleop-ui.js", assets / "teleop-ui.js")
    shutil.copy2(LOGGER_SOURCE, assets / "semantic-logger.js")
    shutil.copy2(OPERATOR_SOURCE, assets / "quest-operator.js")

    manifest = {
        "schema": "spes-hardware-instrumentation-manifest-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_repository": "https://github.com/SpesRobotics/teleop.git",
        "source_commit": commit,
        "upstream_checkout_clean": True,
        "source_index_sha256": sha256(source_index),
        "instrumented_index_sha256": sha256(generated_index),
        "semantic_logger_sha256": sha256(assets / "semantic-logger.js"),
        "quest_operator_sha256": sha256(assets / "quest-operator.js"),
        "control_payload_modified": False,
        "experiment_transport": "separate /experiment WSS",
        "in_xr_hud_fallback": "WebGL stereo world-space Canvas2D panel at 2.5 m",
        "audio_fallback": "speechSynthesis then Web Audio",
        "operator_asset_cache_buster": hashlib.sha256(OPERATOR_SOURCE.read_bytes()).hexdigest()[:16],
        "terminal_markers_required": False,
        "sample_interval_ms": 200,
    }
    manifest_path = output / "INSTRUMENTATION_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"event": "instrumented_frontend_ready", "output": str(output), **manifest}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
