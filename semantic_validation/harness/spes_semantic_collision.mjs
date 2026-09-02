#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const harnessDir = path.dirname(fileURLToPath(import.meta.url));
const validationRoot = path.resolve(harnessDir, "..");
const targetRoot = path.join(validationRoot, "targets", "spes_teleop");
const indexPath = path.join(targetRoot, "teleop", "index.html");
const expectedCommit = "c5d808155a87b584d6147a5943d4b87c34c92db0";

function outputPath() {
    const index = process.argv.indexOf("--output");
    if (index < 0 || !process.argv[index + 1]) throw new Error("--output is required");
    return path.resolve(process.argv[index + 1]);
}

function readGitHead(repositoryRoot) {
    const gitDir = path.join(repositoryRoot, ".git");
    const head = fs.readFileSync(path.join(gitDir, "HEAD"), "utf8").trim();
    if (!head.startsWith("ref: ")) return head;
    const ref = head.slice(5);
    const loose = path.join(gitDir, ref);
    if (fs.existsSync(loose)) return fs.readFileSync(loose, "utf8").trim();
    const line = fs
        .readFileSync(path.join(gitDir, "packed-refs"), "utf8")
        .split("\n")
        .find((candidate) => !candidate.startsWith("#") && candidate.endsWith(` ${ref}`));
    if (!line) throw new Error(`cannot resolve ${ref}`);
    return line.split(" ", 1)[0];
}

function xrPose(emulatedPosition) {
    return {
        emulatedPosition,
        transform: {
            position: { x: 0.25, y: 0.5, z: 0.75 },
            orientation: { x: 0, y: 0, z: 0, w: 1 },
        },
    };
}

async function settlePromises() {
    for (let index = 0; index < 4; index += 1) {
        await new Promise((resolve) => setImmediate(resolve));
    }
}

async function executeState(testState) {
    const html = fs.readFileSync(indexPath, "utf8");
    const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
    assert.equal(scripts.length, 1, "expected the single upstream inline application script");

    const packets = [];
    const sockets = [];
    const startListeners = {};
    const sessionListeners = {};
    let animationFrameCallback = null;
    const button = (pressed = false) => ({ pressed });
    const inputSource = {
        handedness: "right",
        targetRayMode: "tracked-pointer",
        targetRaySpace: { kind: "right-target-ray" },
        gamepad: {
            buttons: [button(false), button(true), button(), button(), button(), button()],
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
    const document = {
        querySelector(selector) {
            return {
                "#teleop-ui": teleopUI,
                "#start-button": {
                    addEventListener(event, callback) {
                        startListeners[event] = callback;
                    },
                },
                "#app": { style: {} },
                "#connection-status": { textContent: "", className: "" },
            }[selector];
        },
        createElement: () => ({ getContext: () => ({ mockedWebGL: true }) }),
    };
    class MockWebSocket {
        static OPEN = 1;

        constructor() {
            this.readyState = MockWebSocket.OPEN;
            sockets.push(this);
        }

        send(payload) {
            packets.push(JSON.parse(payload));
        }
    }
    const session = {
        inputSources: [inputSource],
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
        performance: { now: () => 0 },
        setTimeout() {},
        WebSocket: MockWebSocket,
        XRWebGLLayer: class MockXRWebGLLayer {},
        window: { location: { protocol: "https:", host: "127.0.0.1:4443" } },
    };

    vm.createContext(sandbox);
    vm.runInContext(scripts[0][1], sandbox, { filename: indexPath });
    sockets[0].onopen();
    startListeners.click();
    await settlePromises();
    sessionListeners.inputsourceschange();
    animationFrameCallback(20, {
        getPose: () => testState.controllerPose,
        getViewerPose: () => ({ views: [testState.viewerPose] }),
    });
    const posePackets = packets.filter((packet) => packet.type === "pose");
    assert.equal(posePackets.length, 1);
    return posePackets[0].data;
}

const states = [
    {
        id: "A",
        semantic: {
            source: "RIGHT_CONTROLLER",
            tracking_validity: "VALID",
            emulatedPosition: false,
            move: true,
        },
        controllerPose: xrPose(false),
        viewerPose: xrPose(false),
    },
    {
        id: "B",
        semantic: {
            source: "RIGHT_CONTROLLER",
            tracking_validity: "INFERRED_OR_EMULATED",
            emulatedPosition: true,
            move: true,
        },
        controllerPose: xrPose(true),
        viewerPose: xrPose(false),
    },
    {
        id: "C",
        semantic: {
            source: "VIEWER",
            tracking_validity: "VIEWER_POSE_AVAILABLE",
            emulatedPosition: null,
            move: true,
        },
        controllerPose: null,
        viewerPose: xrPose(false),
    },
];

const commit = readGitHead(targetRoot);
assert.equal(commit, expectedCommit);
const records = [
    {
        experiment: "spes_semantic_collision",
        trial: "run",
        monotonic_timestamp_ns: process.hrtime.bigint().toString(),
        event: "run_start",
        target_commit: commit,
        executed_source: "unmodified upstream teleop/index.html inline script",
        source_kind: "SYNTHETIC_XR",
    },
];
const payloads = [];
for (const state of states) {
    const controlPacket = await executeState(state);
    payloads.push(controlPacket);
    records.push({
        experiment: "spes_semantic_collision",
        trial: `state_${state.id}`,
        monotonic_timestamp_ns: process.hrtime.bigint().toString(),
        event: "control_packet",
        input_semantic_ground_truth: state.semantic,
        control_packet: controlPacket,
        downstream_semantic_fields: {
            source: Object.hasOwn(controlPacket, "source"),
            tracking_validity: Object.hasOwn(controlPacket, "tracking_validity"),
            emulatedPosition: Object.hasOwn(controlPacket, "emulatedPosition"),
        },
    });
}

assert.deepEqual(payloads[0], payloads[1], "A/B must collide at the control representation");
assert.deepEqual(payloads[0], payloads[2], "A/C must collide at the control representation");
records.push({
    experiment: "spes_semantic_collision",
    trial: "summary",
    monotonic_timestamp_ns: process.hrtime.bigint().toString(),
    event: "decision",
    a_equals_b: true,
    a_equals_c: true,
    evidence_level: "CONFIRMED_RUNTIME_SYNTHETIC_SOURCE",
    finding: "SEMANTIC_COLLISION",
    hardware_activation_claimed: false,
    result: "PASS",
});

const output = outputPath();
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, `${records.map((record) => JSON.stringify(record)).join("\n")}\n`);
process.stdout.write(`${JSON.stringify(records.at(-1))}\n`);
