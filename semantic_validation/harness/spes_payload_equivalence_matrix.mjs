#!/usr/bin/env node

// Execute the actual upstream and instrumented inline WebXR applications in
// matched VM sandboxes and compare the production WebSocket bytes.

import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const harnessDir = path.dirname(fileURLToPath(import.meta.url));
const validationRoot = path.resolve(harnessDir, "..");

function argumentsFrom(argv) {
    const values = {
        upstream: path.join(validationRoot, "targets", "spes_teleop", "teleop", "index.html"),
        instrumented: path.join(validationRoot, "instrumented", "spes_frontend", "index.html"),
        semanticLogger: path.join(
            validationRoot,
            "instrumented",
            "spes_frontend",
            "assets",
            "semantic-logger.js"
        ),
        questOperator: path.join(
            validationRoot,
            "instrumented",
            "spes_frontend",
            "assets",
            "quest-operator.js"
        ),
        artifact: "deployed_generated_frontend",
    };
    for (let index = 0; index < argv.length; index += 2) {
        const flag = argv[index];
        const value = argv[index + 1];
        if (!flag || !flag.startsWith("--") || value === undefined) {
            throw new Error(`invalid argument sequence near ${flag || "<end>"}`);
        }
        const key = flag.slice(2).replace(/-([a-z])/g, (_match, letter) => letter.toUpperCase());
        if (!Object.hasOwn(values, key)) throw new Error(`unknown option ${flag}`);
        values[key] = value;
    }
    return values;
}

function sha256(value) {
    return crypto.createHash("sha256").update(value).digest("hex");
}

function transform(x, y, z, options = {}) {
    return {
        emulatedPosition: Boolean(options.emulatedPosition),
        transform: {
            position: { x, y, z },
            orientation: options.orientation || { x: 0, y: 0, z: 0, w: 1 },
        },
    };
}

function viewerPose(specification) {
    if (!specification) return null;
    return {
        emulatedPosition: Boolean(specification.emulatedPosition),
        transform: specification.transform,
        views: [{ transform: specification.transform }],
    };
}

function makeNode() {
    const fields = new Map();
    return {
        style: {},
        textContent: "",
        className: "",
        id: "",
        innerHTML: "",
        appendChild() {},
        addEventListener() {},
        querySelector(selector) {
            if (!fields.has(selector)) fields.set(selector, makeNode());
            return fields.get(selector);
        },
    };
}

async function settlePromises() {
    for (let index = 0; index < 6; index += 1) {
        await new Promise((resolve) => setImmediate(resolve));
    }
}

async function executeFrontend(indexPath, assets, testCase, instrumented) {
    const html = fs.readFileSync(indexPath, "utf8");
    const inlineScripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
    assert.equal(inlineScripts.length, 1, `${indexPath}: expected one inline application script`);

    let monotonicMs = 0;
    let animationFrameCallback = null;
    const startListeners = new Map();
    const sessionListeners = new Map();
    const socketSends = [];
    const sockets = [];
    const localStats = [];

    const ui = {
        move: Boolean(testCase.ui?.move),
        gripper: Boolean(testCase.ui?.gripper),
        scale: testCase.ui?.scale ?? 1,
        reservedA: Boolean(testCase.ui?.reservedA),
        reservedB: Boolean(testCase.ui?.reservedB),
    };
    const teleopUI = {
        style: {},
        addEventListener() {},
        updateServerDiagnostics() {},
        updateLocalStats(state) {
            localStats.push(JSON.parse(JSON.stringify(state)));
        },
        isMotionEnabled: () => ui.move,
        isGripperEngaged: () => ui.gripper,
        isReservedButtonAActive: () => ui.reservedA,
        isReservedButtonBActive: () => ui.reservedB,
        getScale: () => ui.scale,
    };
    const startButton = {
        addEventListener(event, callback) {
            startListeners.set(event, callback);
        },
    };
    const app = makeNode();
    const documentListeners = new Map();
    const canvas2d = {
        clearRect() {},
        fillRect() {},
        strokeRect() {},
        fillText() {},
        set fillStyle(_value) {},
        set strokeStyle(_value) {},
        set lineWidth(_value) {},
        set font(_value) {},
    };
    const mockGl = {};
    const document = {
        visibilityState: "visible",
        head: makeNode(),
        addEventListener(event, callback) {
            if (!documentListeners.has(event)) documentListeners.set(event, []);
            documentListeners.get(event).push(callback);
        },
        querySelector(selector) {
            return {
                "#teleop-ui": teleopUI,
                "#start-button": startButton,
                "#app": app,
                "#connection-status": { textContent: "", className: "" },
            }[selector];
        },
        createElement(tag) {
            const node = makeNode();
            if (tag === "canvas") {
                node.getContext = (kind) => (kind === "2d" ? canvas2d : mockGl);
            }
            return node;
        },
    };

    const gamepad = {
        buttons: Array.from({ length: 6 }, () => ({ pressed: false })),
        axes: [0],
    };
    const inputSources = testCase.rightInput
        ? [
              {
                  handedness: "right",
                  targetRayMode: "tracked-pointer",
                  targetRaySpace: { kind: "right-target-ray" },
                  gamepad,
              },
          ]
        : [];

    class MockWebSocket {
        static OPEN = 1;

        constructor(url) {
            this.url = url;
            this.readyState = MockWebSocket.OPEN;
            sockets.push(this);
        }

        send(data) {
            socketSends.push({ url: this.url, raw: String(data), monotonic_ms: monotonicMs });
        }
    }

    const session = {
        inputSources,
        visibilityState: "visible",
        renderState: {},
        addEventListener(event, callback) {
            if (!sessionListeners.has(event)) sessionListeners.set(event, []);
            sessionListeners.get(event).push(callback);
        },
        updateRenderState(state) {
            this.renderState = state;
        },
        requestReferenceSpace: async () => ({ kind: "local-floor" }),
        requestAnimationFrame(callback) {
            animationFrameCallback = callback;
        },
        end() {},
    };
    const location = { protocol: "https:", host: "127.0.0.1:4443" };
    const sandbox = {
        console: { log() {}, error() {} },
        document,
        navigator: { xr: { requestSession: async () => session } },
        performance: { now: () => monotonicMs },
        setTimeout() {},
        WebSocket: MockWebSocket,
        XRWebGLLayer: class MockXRWebGLLayer {
            getViewport() {
                return { x: 0, y: 0, width: 1, height: 1 };
            }
        },
        location,
        window: { location },
    };
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    if (instrumented) {
        vm.runInContext(fs.readFileSync(assets.semanticLogger, "utf8"), sandbox, {
            filename: assets.semanticLogger,
        });
        vm.runInContext(fs.readFileSync(assets.questOperator, "utf8"), sandbox, {
            filename: assets.questOperator,
        });
    }
    vm.runInContext(inlineScripts[0][1], sandbox, { filename: indexPath });

    const productionSocket = sockets.find((socket) => socket.url.endsWith("/ws"));
    assert.ok(productionSocket, "production WebSocket was not created");
    if (testCase.connected) productionSocket.onopen();
    startListeners.get("click")();
    await settlePromises();
    for (const callback of sessionListeners.get("inputsourceschange") || []) {
        callback({ added: inputSources, removed: [] });
    }

    for (const frameSpec of testCase.frames) {
        monotonicMs = frameSpec.time;
        if (testCase.rightInput) {
            const pressed = frameSpec.buttons || [];
            for (let buttonIndex = 0; buttonIndex < gamepad.buttons.length; buttonIndex += 1) {
                gamepad.buttons[buttonIndex].pressed = Boolean(pressed[buttonIndex]);
            }
            gamepad.axes[0] = frameSpec.axis ?? 0;
        }
        const frame = {
            getPose: () => frameSpec.controllerPose || null,
            getViewerPose: () => viewerPose(frameSpec.viewerPose),
        };
        assert.equal(typeof animationFrameCallback, "function", "XR frame callback unavailable");
        animationFrameCallback(frameSpec.time, frame);
    }

    const productionSends = socketSends.filter((record) => record.url.endsWith("/ws"));
    const poseSends = productionSends
        .filter((record) => JSON.parse(record.raw).type === "pose")
        .map((record) => ({ ...record, parsed: JSON.parse(record.raw) }));
    return {
        poseSends,
        productionSends,
        localStats,
        productionSocketUrl: productionSocket.url,
    };
}

const cases = [
    {
        name: "vr_all_payload_fields",
        rightInput: true,
        connected: true,
        frames: [
            {
                time: 20,
                controllerPose: transform(0.11, -0.22, 0.33, {
                    emulatedPosition: true,
                    orientation: { x: 0.1, y: -0.2, z: 0.3, w: 0.9 },
                }),
                viewerPose: transform(9, 9, 9),
                buttons: [true, true, false, false, true, true],
                axis: -0.5,
            },
        ],
        expectedPoseCount: 1,
        expectedLast: {
            move: true,
            gripper: "close",
            scale: 0.95,
            reservedButtonA: true,
            reservedButtonB: true,
            device: "VR",
            position: { x: 0.11, y: -0.22, z: 0.33 },
        },
    },
    {
        name: "vr_controller_null_viewer_fallback",
        rightInput: true,
        connected: true,
        frames: [
            {
                time: 20,
                controllerPose: null,
                viewerPose: transform(1.1, 1.2, 1.3, {
                    orientation: { x: -0.1, y: 0.2, z: -0.3, w: 0.9 },
                }),
                buttons: [false, true, false, false, false, false],
                axis: 0,
            },
        ],
        expectedPoseCount: 1,
        expectedLast: {
            move: true,
            gripper: "open",
            scale: 1,
            device: "VR",
            position: { x: 1.1, y: 1.2, z: 1.3 },
        },
    },
    {
        name: "phone_ui_all_payload_fields",
        rightInput: false,
        connected: true,
        ui: { move: true, gripper: true, scale: 0.42, reservedA: false, reservedB: true },
        frames: [{ time: 20, controllerPose: null, viewerPose: transform(-1, 2, -3) }],
        expectedPoseCount: 1,
        expectedLast: {
            move: true,
            gripper: "close",
            scale: 0.42,
            reservedButtonA: false,
            reservedButtonB: true,
            device: "Phone",
            position: { x: -1, y: 2, z: -3 },
        },
    },
    {
        name: "no_pose_no_send",
        rightInput: true,
        connected: true,
        frames: [
            {
                time: 20,
                controllerPose: null,
                viewerPose: null,
                buttons: [false, true, false, false, true, true],
            },
        ],
        expectedPoseCount: 0,
    },
    {
        name: "disconnected_no_send",
        rightInput: true,
        connected: false,
        frames: [
            {
                time: 20,
                controllerPose: transform(0.4, 0.5, 0.6),
                viewerPose: null,
                buttons: [false, true, false, false, false, false],
            },
        ],
        expectedPoseCount: 0,
    },
    {
        name: "strict_greater_than_10ms_throttle",
        rightInput: true,
        connected: true,
        frames: [5, 10, 11, 21, 22].map((time) => ({
            time,
            controllerPose: transform(time / 100, 0, 0),
            viewerPose: null,
            buttons: [false, true, false, false, false, false],
        })),
        expectedPoseCount: 2,
        expectedSendTimes: [11, 22],
    },
    {
        name: "vr_controller_state_progression",
        rightInput: true,
        connected: true,
        frames: [
            {
                time: 20,
                controllerPose: transform(0.1, 0, 0),
                buttons: [true, true, false, false, true, false],
                axis: -1,
            },
            {
                time: 40,
                controllerPose: transform(0.2, 0, 0),
                buttons: [false, false, false, false, false, true],
                axis: 0,
            },
            {
                time: 60,
                controllerPose: transform(0.3, 0, 0),
                buttons: [true, true, false, false, true, true],
                axis: 1,
            },
        ],
        expectedPoseCount: 3,
        expectedLast: {
            move: true,
            gripper: "open",
            scale: 1,
            reservedButtonA: true,
            reservedButtonB: true,
            device: "VR",
            position: { x: 0.3, y: 0, z: 0 },
        },
    },
];

const productionPoseKeys = [
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
const forbiddenExperimentKeys = new Set([
    "classification",
    "control_packet_index",
    "controller_emulated_position",
    "emulatedPosition",
    "event_type",
    "experiment",
    "phase",
    "selected_source",
    "server_update_index",
    "trial",
]);

function forbiddenPaths(value, prefix = "data") {
    const paths = [];
    if (!value || typeof value !== "object") return paths;
    for (const [key, child] of Object.entries(value)) {
        const next = `${prefix}.${key}`;
        if (forbiddenExperimentKeys.has(key)) paths.push(next);
        paths.push(...forbiddenPaths(child, next));
    }
    return paths;
}

function assertExpected(payload, expected) {
    for (const [key, value] of Object.entries(expected || {})) {
        if (typeof value === "number") {
            assert.ok(Math.abs(payload[key] - value) < 1e-12, `${key}: ${payload[key]} != ${value}`);
        } else {
            assert.deepEqual(payload[key], value, `${key} mismatch`);
        }
    }
}

const options = argumentsFrom(process.argv.slice(2));
const assets = {
    semanticLogger: options.semanticLogger,
    questOperator: options.questOperator,
};
const results = [];
for (const testCase of cases) {
    const upstream = await executeFrontend(options.upstream, assets, testCase, false);
    const instrumented = await executeFrontend(options.instrumented, assets, testCase, true);
    const upstreamRaw = upstream.poseSends.map((record) => record.raw);
    const instrumentedRaw = instrumented.poseSends.map((record) => record.raw);
    const upstreamTimes = upstream.poseSends.map((record) => record.monotonic_ms);
    const instrumentedTimes = instrumented.poseSends.map((record) => record.monotonic_ms);
    assert.deepEqual(instrumentedRaw, upstreamRaw, `${testCase.name}: serialized pose bytes changed`);
    assert.deepEqual(instrumentedTimes, upstreamTimes, `${testCase.name}: send timing changed`);
    assert.equal(upstreamRaw.length, testCase.expectedPoseCount, `${testCase.name}: unexpected send count`);
    if (testCase.expectedSendTimes) {
        assert.deepEqual(upstreamTimes, testCase.expectedSendTimes, `${testCase.name}: throttle boundary changed`);
    }
    assert.deepEqual(instrumented.localStats, upstream.localStats, `${testCase.name}: local state changed`);
    for (const record of instrumented.poseSends) {
        assert.deepEqual(Object.keys(record.parsed).sort(), ["data", "type"]);
        assert.equal(record.parsed.type, "pose");
        assert.deepEqual(Object.keys(record.parsed.data).sort(), productionPoseKeys);
        assert.deepEqual(forbiddenPaths(record.parsed.data), []);
    }
    if (testCase.expectedLast) {
        assertExpected(upstream.poseSends.at(-1).parsed.data, testCase.expectedLast);
    }
    results.push({
        case: testCase.name,
        pose_send_count: upstreamRaw.length,
        pose_send_monotonic_ms: upstreamTimes,
        serialized_pose_sha256: upstreamRaw.map(sha256),
        exact_serialization_equal: true,
        key_set_equal: true,
        values_equal: true,
        send_condition_equal: true,
        local_stats_equal: true,
        experiment_fields_in_pose_payload: false,
        result: "PASS",
    });
}

process.stdout.write(
    `${JSON.stringify({
        event: "spes_payload_equivalence_matrix",
        artifact: options.artifact,
        upstream_index: path.resolve(options.upstream),
        instrumented_index: path.resolve(options.instrumented),
        semantic_logger: path.resolve(options.semanticLogger),
        quest_operator: path.resolve(options.questOperator),
        production_pose_fields: productionPoseKeys,
        case_count: results.length,
        cases: results,
        exact_serialization_equal: true,
        send_condition_equal: true,
        experiment_fields_in_pose_payload: false,
        result: "PASS",
    })}\n`
);
