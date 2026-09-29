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

function outputPathFromArgs() {
    const index = process.argv.indexOf("--output");
    if (index === -1) return null;
    if (!process.argv[index + 1]) throw new Error("--output requires a path");
    return path.resolve(process.argv[index + 1]);
}

function readGitHead(repositoryRoot) {
    const gitDir = path.join(repositoryRoot, ".git");
    const head = fs.readFileSync(path.join(gitDir, "HEAD"), "utf8").trim();
    if (!head.startsWith("ref: ")) return head;
    const ref = head.slice(5);
    const looseRef = path.join(gitDir, ref);
    if (fs.existsSync(looseRef)) return fs.readFileSync(looseRef, "utf8").trim();
    const packedRefs = fs.readFileSync(path.join(gitDir, "packed-refs"), "utf8");
    const match = packedRefs
        .split("\n")
        .find((line) => !line.startsWith("#") && line.endsWith(` ${ref}`));
    if (!match) throw new Error(`cannot resolve Git ref ${ref}`);
    return match.split(" ", 1)[0];
}

function pose(x, y, z) {
    return {
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

async function runActualFrontendCase({ name, controllerPose, viewerPose, move }) {
    const html = fs.readFileSync(indexPath, "utf8");
    const inlineScripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
    assert.equal(inlineScripts.length, 1, "expected one inline application script");

    const sent = [];
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
            buttons: [button(false), button(move), button(), button(), button(), button()],
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
    const app = { style: {} };
    const connectionStatus = { textContent: "", className: "" };

    const document = {
        querySelector(selector) {
            return {
                "#teleop-ui": teleopUI,
                "#start-button": startButton,
                "#app": app,
                "#connection-status": connectionStatus,
            }[selector];
        },
        createElement(tag) {
            assert.equal(tag, "canvas");
            return { getContext: () => ({ mockedWebGL: true }) };
        },
    };

    class MockWebSocket {
        static OPEN = 1;

        constructor(url) {
            this.url = url;
            this.readyState = MockWebSocket.OPEN;
            sockets.push(this);
        }

        send(data) {
            sent.push(JSON.parse(data));
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
    vm.runInContext(inlineScripts[0][1], sandbox, { filename: indexPath });
    assert.equal(sockets.length, 1);
    sockets[0].onopen();
    startListeners.click();
    await settlePromises();

    assert.ok(sessionListeners.inputsourceschange, "inputsourceschange handler not installed");
    sessionListeners.inputsourceschange();
    assert.ok(animationFrameCallback, "XR animation frame handler not installed");

    const frame = {
        getPose: () => controllerPose,
        getViewerPose: () =>
            viewerPose === null ? null : { views: [viewerPose] },
    };
    animationFrameCallback(20, frame);

    assert.equal(sent.length, 1, `${name}: one WebSocket packet expected`);
    const packet = sent[0];
    assert.equal(packet.type, "pose");
    assert.equal(packet.data.move, move);
    assert.equal(packet.data.device, "VR");
    assert.equal("source" in packet.data, false);
    assert.equal("tracking_valid" in packet.data, false);
    assert.equal("emulatedPosition" in packet.data, false);
    assert.equal("timestamp" in packet.data, false);

    return packet.data;
}

const cases = [
    {
        name: "controller_available",
        controllerPose: pose(0.1, 0.2, 0.3),
        viewerPose: pose(9, 9, 9),
        move: false,
        expectedPosition: { x: 0.1, y: 0.2, z: 0.3 },
        expectedSelectedSource: "controller",
    },
    {
        name: "controller_unavailable_viewer_available",
        controllerPose: null,
        viewerPose: pose(1.1, 1.2, 1.3),
        move: false,
        expectedPosition: { x: 1.1, y: 1.2, z: 1.3 },
        expectedSelectedSource: "viewer",
    },
    {
        name: "viewer_fallback_with_move_true",
        controllerPose: null,
        viewerPose: pose(2.1, 2.2, 2.3),
        move: true,
        expectedPosition: { x: 2.1, y: 2.2, z: 2.3 },
        expectedSelectedSource: "viewer",
    },
];

const records = [];
const commit = readGitHead(targetRoot);
records.push({
    event: "run_start",
    harness: "spes_frontend_s1",
    target_commit: commit,
    executed_source: "teleop/index.html inline script",
    time_utc: new Date().toISOString(),
    node: process.version,
});

for (const testCase of cases) {
    const actual = await runActualFrontendCase(testCase);
    assert.deepEqual(actual.position, testCase.expectedPosition);
    records.push({
        event: "case_result",
        case: testCase.name,
        selected_source_observed: testCase.expectedSelectedSource,
        move: actual.move,
        payload: actual,
        source_identity_fields_present: false,
        result: "PASS",
    });
}

records.push({
    event: "summary",
    controller_path: "PASS",
    controller_to_viewer_fallback: "PASS",
    viewer_fallback_with_move_true: "PASS",
    result: "PASS",
});

const rendered = `${records.map((record) => JSON.stringify(record)).join("\n")}\n`;
const outputPath = outputPathFromArgs();
if (outputPath !== null) {
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, rendered);
}
process.stdout.write(rendered);
