#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const harnessDir = path.dirname(fileURLToPath(import.meta.url));
const validationRoot = path.resolve(harnessDir, "..");
const upstreamIndex = path.join(validationRoot, "targets", "spes_teleop", "teleop", "index.html");
const instrumentedRoot = path.join(validationRoot, "instrumented", "spes_frontend");
const instrumentedIndex = path.join(instrumentedRoot, "index.html");
const semanticLoggerSource = path.join(instrumentedRoot, "assets", "semantic-logger.js");
const questOperatorSource = path.join(instrumentedRoot, "assets", "quest-operator.js");

function pose(x, y, z, emulatedPosition = false) {
    return {
        emulatedPosition,
        transform: {
            position: { x, y, z },
            orientation: { x: 0, y: 0, z: 0, w: 1 },
        },
    };
}

async function settlePromises() {
    for (let i = 0; i < 4; i += 1) {
        await new Promise((resolve) => setImmediate(resolve));
    }
}

async function executeFrontend(indexPath, testCase, instrumented) {
    const html = fs.readFileSync(indexPath, "utf8");
    const inlineScripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
    assert.equal(inlineScripts.length, 1, "expected one inline application script");

    const sent = [];
    const sockets = [];
    const startListeners = {};
    const sessionListeners = {};
    let animationFrameCallback = null;
    let monotonicMs = 0;
    let viewerPoseCalls = 0;

    const button = (pressed = false) => ({ pressed });
    const inputSource = {
        handedness: "right",
        targetRayMode: "tracked-pointer",
        targetRaySpace: { kind: "right-target-ray" },
        gamepad: {
            buttons: [button(false), button(testCase.move), button(), button(), button(), button()],
            axes: [0],
        },
    };
    const teleopUI = {
        style: {},
        addEventListener() {},
        updateServerDiagnostics() {},
        updateLocalStats() {},
        isMotionEnabled: () => false,
        isGripperEngaged: () => false,
        isReservedButtonAActive: () => false,
        isReservedButtonBActive: () => false,
        getScale: () => 1,
    };
    const startButton = {
        addEventListener(event, callback) {
            startListeners[event] = callback;
        },
    };
    const makeNode = () => {
        const fields = new Map();
        return {
            style: {},
            textContent: "",
            className: "",
            appendChild() {},
            querySelector(selector) {
                if (!fields.has(selector)) fields.set(selector, makeNode());
                return fields.get(selector);
            },
        };
    };
    const app = makeNode();
    const document = {
        visibilityState: "visible",
        head: makeNode(),
        addEventListener() {},
        querySelector(selector) {
            return {
                "#teleop-ui": teleopUI,
                "#start-button": startButton,
                "#app": app,
                "#connection-status": { textContent: "", className: "" },
            }[selector];
        },
        createElement: () => ({ ...makeNode(), getContext: () => ({ mockedWebGL: true }) }),
    };
    class MockWebSocket {
        static OPEN = 1;

        constructor() {
            this.readyState = MockWebSocket.OPEN;
            sockets.push(this);
        }

        send(data) {
            sent.push(JSON.parse(data));
        }
    }
    const session = {
        inputSources: [inputSource],
        visibilityState: "visible",
        addEventListener(event, callback) {
            sessionListeners[event] = callback;
        },
        updateRenderState() {},
        requestReferenceSpace: async () => ({ kind: "local-floor" }),
        requestAnimationFrame(callback) {
            animationFrameCallback = callback;
        },
        end() {},
    };
    const sandbox = {
        console: { log() {}, error() {} },
        document,
        navigator: { xr: { requestSession: async () => session } },
        performance: { now: () => monotonicMs },
        setTimeout() {},
        WebSocket: MockWebSocket,
        XRWebGLLayer: class MockXRWebGLLayer {},
        window: { location: { protocol: "https:", host: "127.0.0.1:4443" } },
    };
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    if (instrumented) {
        vm.runInContext(fs.readFileSync(semanticLoggerSource, "utf8"), sandbox, {
            filename: semanticLoggerSource,
        });
        vm.runInContext(fs.readFileSync(questOperatorSource, "utf8"), sandbox, {
            filename: questOperatorSource,
        });
    }
    vm.runInContext(inlineScripts[0][1], sandbox, { filename: indexPath });
    sockets[0].onopen();
    startListeners.click();
    await settlePromises();
    sessionListeners.inputsourceschange();
    const frame = {
        getPose: () => testCase.controllerPose,
        getViewerPose: () => {
            viewerPoseCalls += 1;
            return testCase.viewerPose === null
                ? null
                : {
                      emulatedPosition: testCase.viewerEmulatedPosition,
                      views: [testCase.viewerPose],
                  };
        },
    };
    for (const frameTime of [20, 30, 230]) {
        monotonicMs = frameTime;
        animationFrameCallback(frameTime, frame);
    }
    return { sent, viewerPoseCalls };
}

const cases = [
    {
        name: "controller_emulated_true",
        controllerPose: pose(0.1, 0.2, 0.3, true),
        viewerPose: pose(9, 9, 9),
        viewerEmulatedPosition: false,
        move: true,
        selectedSource: "CONTROLLER",
    },
    {
        name: "controller_null_viewer_fallback",
        controllerPose: null,
        viewerPose: pose(1.1, 1.2, 1.3),
        viewerEmulatedPosition: false,
        move: true,
        selectedSource: "VIEWER_FALLBACK",
    },
];

const requiredSemanticFields = [
    "xr_frame_time",
    "local_monotonic_ms",
    "is_vr_device",
    "input_source_count",
    "right_controller_input_source_present",
    "controller_pose_exists",
    "controller_emulated_position",
    "controller_pose",
    "viewer_pose_exists",
    "viewer_emulated_position",
    "viewer_pose",
    "selected_source",
    "move",
    "gripper",
    "websocket_connected",
    "control_packet_index",
];
const productionPoseFields = [
    "device",
    "fps",
    "gripper",
    "message",
    "move",
    "orientation",
    "position",
    "reservedButtonA",
    "reservedButtonB",
    "scale",
];

const results = [];
for (const testCase of cases) {
    const upstreamRun = await executeFrontend(upstreamIndex, testCase, false);
    const instrumentedRun = await executeFrontend(instrumentedIndex, testCase, true);
    const upstreamPose = upstreamRun.sent.filter((packet) => packet.type === "pose");
    const instrumentedPose = instrumentedRun.sent.filter((packet) => packet.type === "pose");
    assert.deepEqual(instrumentedPose, upstreamPose, `${testCase.name}: control payload changed`);
    for (const packet of instrumentedPose) {
        assert.deepEqual(Object.keys(packet.data).sort(), productionPoseFields);
        assert.ok(!Object.hasOwn(packet.data, "experiment"));
        assert.ok(!Object.hasOwn(packet.data, "classification"));
        assert.ok(!Object.hasOwn(packet.data, "emulatedPosition"));
    }

    const allFrameSemanticEvents = instrumentedRun.sent
        .filter((packet) => packet.type === "log")
        .map((packet) => JSON.parse(packet.data))
        .filter((event) => ["semantic_transition", "semantic_sample"].includes(event.event_kind));
    assert.equal(allFrameSemanticEvents.length, 2, `${testCase.name}: expected transition plus 5 Hz sample`);
    const semanticEvents = allFrameSemanticEvents.filter(
        (event) => event.event_kind === "semantic_transition"
    );
    assert.ok(semanticEvents.length >= 1, `${testCase.name}: missing semantic transition`);
    const semantic = semanticEvents.at(-1);
    for (const field of requiredSemanticFields) {
        assert.ok(Object.hasOwn(semantic, field), `${testCase.name}: missing ${field}`);
    }
    assert.equal(semantic.selected_source, testCase.selectedSource);
    assert.equal(semantic.move, testCase.move);
    assert.equal(semantic.control_packet_index, 1);
    if (testCase.controllerPose) {
        assert.equal(semantic.controller_pose_exists, true);
        assert.equal(semantic.controller_emulated_position, true);
    } else {
        assert.equal(semantic.controller_pose_exists, false);
        assert.equal(semantic.controller_emulated_position, null);
    }
    if (testCase.controllerPose) {
        assert.equal(instrumentedRun.viewerPoseCalls, 2, "non-selected viewer must be sampled, not read every frame");
        assert.equal(upstreamRun.viewerPoseCalls, 0);
    } else {
        assert.equal(instrumentedRun.viewerPoseCalls, upstreamRun.viewerPoseCalls);
    }
    results.push({
        case: testCase.name,
        control_payload_identical: true,
        control_payload_fields: productionPoseFields,
        experiment_fields_in_control_payload: false,
        selected_source: semantic.selected_source,
        controller_emulated_position: semantic.controller_emulated_position,
        sideband_after_control_packet_index: semantic.control_packet_index,
        frame_semantic_event_count_for_210ms: allFrameSemanticEvents.length,
        nonselected_viewer_read_every_frame: false,
        result: "PASS",
    });
}

process.stdout.write(
    `${JSON.stringify({
        event: "hardware_frontend_selftest",
        source: "generated actual Spes onXRFrame",
        cases: results,
        result: "PASS",
    })}\n`
);
