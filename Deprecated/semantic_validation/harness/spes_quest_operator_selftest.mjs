#!/usr/bin/env node

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const harnessDir = path.dirname(fileURLToPath(import.meta.url));
const sourcePath = path.resolve(harnessDir, "..", "instrumentation", "quest-operator.js");
const source = fs.readFileSync(sourcePath, "utf8");

let monotonicMs = 0;
const spoken = [];
const beepStarts = [];
const sidebandPackets = [];
const listeners = {};
const canvas2d = {
    clearRect() {},
    fillRect() {},
    strokeRect() {},
    fillText() {},
    fillStyle: "",
    strokeStyle: "",
    lineWidth: 0,
    font: "",
};

function node() {
    const children = new Map();
    return {
        style: {},
        textContent: "",
        className: "",
        appendChild() {},
        querySelector(selector) {
            if (!children.has(selector)) children.set(selector, node());
            return children.get(selector);
        },
    };
}

class MockWebSocket {
    static OPEN = 1;

    constructor(url) {
        this.url = url;
        this.readyState = 0;
    }

    send(payload) {
        sidebandPackets.push(JSON.parse(payload));
    }
}

class MockAudioContext {
    constructor() {
        this.currentTime = 0;
        this.destination = {};
    }

    resume() {
        return Promise.resolve();
    }

    createOscillator() {
        return {
            frequency: { value: 0 },
            connect() {},
            start(value) { beepStarts.push(value); },
            stop() {},
        };
    }

    createGain() {
        return { gain: { value: 0 }, connect() {} };
    }
}

const app = node();
const sandbox = {
    console: { log() {}, error() {} },
    Date,
    JSON,
    performance: { now: () => monotonicMs },
    setTimeout() {},
    WebSocket: MockWebSocket,
    AudioContext: MockAudioContext,
    SpeechSynthesisUtterance: class {
        constructor(text) { this.text = text; }
    },
    speechSynthesis: { speak: (utterance) => spoken.push(utterance.text) },
    location: { protocol: "https:", host: "192.0.2.10:4443" },
    document: {
        visibilityState: "visible",
        head: node(),
        querySelector: (selector) => selector === "#app" ? app : null,
        createElement: () => ({ ...node(), getContext: () => canvas2d }),
        addEventListener() {},
    },
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(source, sandbox, { filename: sourcePath });

const session = {
    visibilityState: "visible",
    domOverlayState: { type: "screen" },
    addEventListener(name, callback) {
        if (!listeners[name]) listeners[name] = [];
        listeners[name].push(callback);
    },
};
const sockets = [];
const operator = new sandbox.SpesQuestExperimentOperator({
    socketFactory(url) {
        const socket = new MockWebSocket(url);
        sockets.push(socket);
        return socket;
    },
});
operator.onProductionWebSocket("open");
assert.equal(sockets.length, 1);
assert.equal(sockets[0].url, "wss://192.0.2.10:4443/experiment");
sockets[0].readyState = MockWebSocket.OPEN;
sockets[0].onopen();
operator.onSessionStarted(session);

const controllerPose = {
    emulatedPosition: false,
    position: { x: 0, y: 1, z: 0 },
    orientation: { x: 0, y: 0, z: 0, w: 1 },
};
function observation() {
    return {
        xrFrameTime: monotonicMs,
        rightControllerInputSourcePresent: true,
        controllerPose,
        viewerPose: { views: [{ transform: controllerPose }] },
        viewerPoseSampled: true,
        selectedSource: "CONTROLLER",
        move: true,
        controlPacketIndex: Math.floor(monotonicMs / 10),
    };
}

monotonicMs = 0;
operator.onFrame(observation());
monotonicMs = 600;
operator.onFrame(observation());
assert.equal(operator.getStateForTest().phase, "READY", "stable production move must confirm mapping");

const leftSource = { handedness: "left" };
const rightSource = { handedness: "right" };
monotonicMs = 700;
for (const callback of listeners.selectstart) callback({ inputSource: rightSource });
monotonicMs = 800;
for (const callback of listeners.selectend) callback({ inputSource: rightSource });
assert.equal(operator.getStateForTest().phase, "READY", "right controller must not control experiment");

monotonicMs = 900;
for (const callback of listeners.selectstart) callback({ inputSource: leftSource });
monotonicMs = 1000;
for (const callback of listeners.selectend) callback({ inputSource: leftSource });
assert.equal(operator.getStateForTest().phase, "HOLD_MOVE", "left short press must start T0");

monotonicMs = 1200;
for (const callback of listeners.selectstart) callback({ inputSource: leftSource });
monotonicMs = 3300;
for (const callback of listeners.selectend) callback({ inputSource: leftSource });
assert.equal(operator.getStateForTest().phase, "INVALID", "left long press must abort");
monotonicMs = 5000;
operator.onFrame(observation());
assert.equal(operator.getStateForTest().phase, "READY", "manual abort must return to ready");

assert.equal(operator.getStateForTest().domOverlayType, "screen");
assert.ok(spoken.includes("Experiment ready"), "speech cue missing");
assert.ok(sidebandPackets.some((packet) => packet.data.event_type === "operator_preflight"));
assert.ok(!source.includes("teleopJoystick"), "operator layer must not reach production joystick state");

const trialListeners = {};
const trialSession = {
    visibilityState: "visible",
    domOverlayState: { type: "screen" },
    addEventListener(name, callback) {
        if (!trialListeners[name]) trialListeners[name] = [];
        trialListeners[name].push(callback);
    },
};
let trialSocket;
const trialOperator = new sandbox.SpesQuestExperimentOperator({
    config: {
        stableMoveMs: 10,
        t0DurationMs: 20,
        baselineDurationMs: 10,
        occlusionMaxMs: 30,
        postLossObserveMs: 10,
        recoveryDurationMs: 10,
    },
    socketFactory(url) {
        trialSocket = new MockWebSocket(url);
        return trialSocket;
    },
});
trialOperator.onProductionWebSocket("open");
trialSocket.readyState = MockWebSocket.OPEN;
trialSocket.onopen();
trialOperator.onSessionStarted(trialSession);
let packetIndex = 1;
let serverIndex = 1;
let callbackCount = 0;
function ack({ jumpReject = false, callbackEmitted = true } = {}) {
    if (callbackEmitted) callbackCount += 1;
    trialSocket.onmessage({ data: JSON.stringify({
        type: "server_ack",
        server_update_index: serverIndex,
        callback_emitted: callbackEmitted,
        callback_count: callbackCount,
        jump_reject: jumpReject,
        target_delta: { linear_m: 0.001, angular_rad: 0.001 },
    }) });
}
function trialObservation(emulatedPosition = false, move = true) {
    return {
        xrFrameTime: monotonicMs,
        rightControllerInputSourcePresent: true,
        controllerPose: { ...controllerPose, emulatedPosition },
        viewerPose: { views: [{ transform: controllerPose }] },
        viewerPoseSampled: true,
        selectedSource: "CONTROLLER",
        move,
        controlPacketIndex: packetIndex,
    };
}
function leftPress(at) {
    monotonicMs = at;
    for (const callback of trialListeners.selectstart) callback({ inputSource: leftSource });
    monotonicMs = at + 1;
    for (const callback of trialListeners.selectend) callback({ inputSource: leftSource });
}
ack();
monotonicMs = 0;
trialOperator.onFrame(trialObservation());
monotonicMs = 11;
packetIndex += 1;
trialOperator.onFrame(trialObservation());
assert.equal(trialOperator.phase, "READY");
leftPress(12);
monotonicMs = 14;
trialOperator.onFrame(trialObservation());
monotonicMs = 25;
packetIndex += 1;
trialOperator.onFrame(trialObservation());
assert.equal(trialOperator.phase, "BASELINE");
monotonicMs = 50;
packetIndex += 1;
serverIndex += 1;
ack();
trialOperator.onFrame(trialObservation());
assert.equal(trialOperator.phase, "COMPLETE", "T0 should require packet and ACK progress");
leftPress(51);
assert.equal(trialOperator.test, "T1");
leftPress(53);
monotonicMs = 55;
trialOperator.onFrame(trialObservation());
monotonicMs = 66;
packetIndex += 1;
trialOperator.onFrame(trialObservation());
monotonicMs = 77;
packetIndex += 1;
trialOperator.onFrame(trialObservation());
assert.equal(trialOperator.phase, "OCCLUDE");
// A reject before semantic loss is baseline noise and must not change the
// recovery label. This reproduces the hardware trial-1 classifier defect.
serverIndex += 1;
ack({ jumpReject: true, callbackEmitted: false });
monotonicMs = 78;
packetIndex += 1;
trialOperator.onFrame(trialObservation(true));
assert.equal(trialOperator.phase, "LOSS_DETECTED");
monotonicMs = 89;
packetIndex += 1;
serverIndex += 1;
ack();
trialOperator.onFrame(trialObservation(true));
assert.equal(trialOperator.phase, "RESTORE");
monotonicMs = 90;
packetIndex += 1;
serverIndex += 1;
ack();
trialOperator.onFrame(trialObservation(false));
assert.equal(trialOperator.phase, "RECOVERY");
monotonicMs = 101;
packetIndex += 1;
serverIndex += 1;
ack();
trialOperator.onFrame(trialObservation(false));
assert.equal(trialOperator.phase, "COMPLETE");
assert.equal(trialOperator.currentTrial.classification, "HW_EMULATED_CONTINUES");
assert.equal(trialOperator.currentTrial.recovery_classification, "RECOVERY_CONTINUOUS",
    "pre-loss jump reject must be excluded from recovery classification");
assert.equal(trialOperator.validTrials, 1);

// A reject after the semantic-loss boundary is recovery evidence and must be
// retained. Run a second complete trial to cover the opposite boundary.
leftPress(102);
leftPress(104);
monotonicMs = 106;
trialOperator.onFrame(trialObservation());
monotonicMs = 117;
packetIndex += 1;
trialOperator.onFrame(trialObservation());
monotonicMs = 128;
packetIndex += 1;
trialOperator.onFrame(trialObservation());
assert.equal(trialOperator.phase, "OCCLUDE");
monotonicMs = 129;
packetIndex += 1;
trialOperator.onFrame(trialObservation(true));
serverIndex += 1;
ack({ jumpReject: true, callbackEmitted: false });
monotonicMs = 140;
packetIndex += 1;
trialOperator.onFrame(trialObservation(true));
assert.equal(trialOperator.phase, "RESTORE");
serverIndex += 1;
ack();
monotonicMs = 141;
packetIndex += 1;
trialOperator.onFrame(trialObservation(false));
serverIndex += 1;
ack();
monotonicMs = 152;
packetIndex += 1;
trialOperator.onFrame(trialObservation(false));
assert.equal(trialOperator.currentTrial.recovery_classification,
    "RECOVERY_JUMP_REJECT_THEN_REANCHOR",
    "post-loss jump reject must remain recovery evidence");
assert.equal(trialOperator.validTrials, 2);

// Invalid critical-window attempts must never consume a valid-trial slot.
leftPress(153);
leftPress(155);
monotonicMs = 157;
trialOperator.onFrame(trialObservation());
monotonicMs = 168;
packetIndex += 1;
trialOperator.onFrame(trialObservation());
monotonicMs = 179;
packetIndex += 1;
trialOperator.onFrame(trialObservation());
assert.equal(trialOperator.phase, "OCCLUDE");
monotonicMs = 180;
trialOperator.onFrame(trialObservation(false, false));
assert.equal(trialOperator.phase, "INVALID");
assert.equal(trialOperator.validTrials, 2, "move-release invalid trial must be excluded");

monotonicMs = 5000;
trialOperator.onFrame(trialObservation());
assert.equal(trialOperator.phase, "READY");
leftPress(5001);
monotonicMs = 5003;
trialOperator.onFrame(trialObservation());
monotonicMs = 5014;
packetIndex += 1;
trialOperator.onFrame(trialObservation());
monotonicMs = 5025;
packetIndex += 1;
trialOperator.onFrame(trialObservation());
assert.equal(trialOperator.phase, "OCCLUDE");
trialSession.visibilityState = "hidden";
monotonicMs = 5026;
for (const callback of trialListeners.visibilitychange) callback();
assert.equal(trialOperator.phase, "INVALID");
assert.equal(trialOperator.validTrials, 2, "focus-invalid trial must be excluded");
trialSession.visibilityState = "visible";

let drawCalls = 0;
const mockGl = {
    VERTEX_SHADER: 1, FRAGMENT_SHADER: 2, COMPILE_STATUS: 3, LINK_STATUS: 4,
    ARRAY_BUFFER: 5, STATIC_DRAW: 6, TEXTURE_2D: 7, TEXTURE_MIN_FILTER: 8,
    TEXTURE_MAG_FILTER: 9, LINEAR: 10, TEXTURE_WRAP_S: 11, TEXTURE_WRAP_T: 12,
    CLAMP_TO_EDGE: 13, UNPACK_FLIP_Y_WEBGL: 14, FRAMEBUFFER: 15, RGBA: 16,
    UNSIGNED_BYTE: 17, FLOAT: 18, TEXTURE0: 19, DEPTH_TEST: 20, BLEND: 21,
    SRC_ALPHA: 22, ONE_MINUS_SRC_ALPHA: 23, TRIANGLES: 24,
    createShader: () => ({}), shaderSource() {}, compileShader() {},
    getShaderParameter: () => true, getShaderInfoLog: () => "",
    createProgram: () => ({}), attachShader() {}, linkProgram() {},
    getProgramParameter: () => true, getProgramInfoLog: () => "",
    getAttribLocation: (_program, name) => name === "a_position" ? 0 : 1,
    getUniformLocation: () => ({}), createBuffer: () => ({}), bindBuffer() {},
    bufferData() {}, createTexture: () => ({}), bindTexture() {}, texParameteri() {},
    pixelStorei() {}, bindFramebuffer() {}, texImage2D() {}, useProgram() {},
    enableVertexAttribArray() {}, vertexAttribPointer() {}, activeTexture() {},
    uniform1i() {}, uniformMatrix4fv() {}, disable() {}, enable() {}, blendFunc() {}, viewport() {},
    drawArrays() { drawCalls += 1; },
};
const xrHudSession = {
    visibilityState: "visible",
    domOverlayState: null,
    renderState: {
        baseLayer: {
            framebuffer: {},
            getViewport: () => ({ x: 0, y: 0, width: 1024, height: 1024 }),
        },
    },
    addEventListener() {},
};
const xrHudOperator = new sandbox.SpesQuestExperimentOperator({ socketFactory: (url) => new MockWebSocket(url) });
xrHudOperator.onSessionStarted(xrHudSession);
assert.equal(xrHudOperator.attachXRRenderer(mockGl, xrHudSession), true);
const identityMatrix = new Float32Array([
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1,
]);
xrHudOperator.renderXRFrame({
    getViewerPose: () => ({
        transform: { matrix: identityMatrix },
        views: [{
            projectionMatrix: identityMatrix,
            transform: { inverse: { matrix: identityMatrix } },
        }],
    }),
}, {});
assert.equal(drawCalls, 1, "in-XR WebGL fallback HUD must draw once per view");

const noSpeechSandbox = { ...sandbox, speechSynthesis: null, SpeechSynthesisUtterance: null };
noSpeechSandbox.globalThis = noSpeechSandbox;
vm.createContext(noSpeechSandbox);
vm.runInContext(source, noSpeechSandbox, { filename: sourcePath });
const beepOperator = new noSpeechSandbox.SpesQuestExperimentOperator({ socketFactory: (url) => new MockWebSocket(url) });
beepOperator._announce("beep fallback", [0.05, 0.05]);
assert.ok(beepStarts.length >= 2, "Web Audio fallback pattern missing");

process.stdout.write(`${JSON.stringify({
    event: "quest_operator_selftest",
    dom_overlay_runtime_check: true,
    speech_cue: true,
    web_audio_fallback: true,
    left_short_press: true,
    left_long_press_abort: true,
    right_controller_isolation: true,
    experiment_sideband_wss: true,
    t0_packet_ack_gate: true,
    t1_emulated_classification: "HW_EMULATED_CONTINUES",
    recovery_classification: "RECOVERY_CONTINUOUS",
    pre_loss_jump_reject_excluded: true,
    post_loss_jump_reject_included: true,
    invalid_move_excluded: true,
    invalid_focus_excluded: true,
    in_xr_webgl_hud_fallback: true,
    result: "PASS",
})}\n`);
