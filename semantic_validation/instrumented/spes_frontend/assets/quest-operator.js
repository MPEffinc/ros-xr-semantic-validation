(function (global) {
    "use strict";

    const CONFIG = Object.freeze({
        stableMoveMs: 500,
        t0DurationMs: 5000,
        baselineDurationMs: 1500,
        occlusionMaxMs: 5000,
        postLossObserveMs: 1500,
        recoveryDurationMs: 2500,
        rawSampleIntervalMs: 200,
        invalidDisplayMs: 1500,
    });

    function nowMs() {
        return performance.now();
    }

    function finite(value) {
        return Number.isFinite(value) ? value : null;
    }

    function snapshotTransform(transform) {
        if (!transform) return null;
        return {
            position: {
                x: finite(transform.position && transform.position.x),
                y: finite(transform.position && transform.position.y),
                z: finite(transform.position && transform.position.z),
            },
            orientation: {
                x: finite(transform.orientation && transform.orientation.x),
                y: finite(transform.orientation && transform.orientation.y),
                z: finite(transform.orientation && transform.orientation.z),
                w: finite(transform.orientation && transform.orientation.w),
            },
        };
    }

    function websocketUrl(path) {
        const protocol = global.location && global.location.protocol === "https:" ? "wss:" : "ws:";
        const host = global.location ? global.location.host : "127.0.0.1:4443";
        return `${protocol}//${host}${path}`;
    }

    class XRHudRenderer {
        constructor(gl, session) {
            this.gl = gl;
            this.session = session;
            this.canvas = document.createElement("canvas");
            this.canvas.width = 1024;
            this.canvas.height = 1024;
            this.context = this.canvas.getContext("2d");
            if (!this.context) throw new Error("Canvas2D is unavailable");
            this.program = this._createProgram();
            this.positionLocation = gl.getAttribLocation(this.program, "a_position");
            this.uvLocation = gl.getAttribLocation(this.program, "a_uv");
            this.textureLocation = gl.getUniformLocation(this.program, "u_texture");
            this.mvpLocation = gl.getUniformLocation(this.program, "u_mvp");
            this.buffer = gl.createBuffer();
            gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
            gl.bufferData(
                gl.ARRAY_BUFFER,
                new Float32Array([
                    -0.50, -0.50, 0, 0, 0,
                     0.50, -0.50, 0, 1, 0,
                    -0.50,  0.50, 0, 0, 1,
                    -0.50,  0.50, 0, 0, 1,
                     0.50, -0.50, 0, 1, 0,
                     0.50,  0.50, 0, 1, 1,
                ]),
                gl.STATIC_DRAW
            );
            this.texture = gl.createTexture();
            gl.bindTexture(gl.TEXTURE_2D, this.texture);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
            gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
            this.dirty = true;
            this.lastSignature = null;
            this.lastDrawMs = Number.NEGATIVE_INFINITY;
        }

        _shader(type, source) {
            const shader = this.gl.createShader(type);
            this.gl.shaderSource(shader, source);
            this.gl.compileShader(shader);
            if (!this.gl.getShaderParameter(shader, this.gl.COMPILE_STATUS)) {
                throw new Error(this.gl.getShaderInfoLog(shader) || "WebGL shader compilation failed");
            }
            return shader;
        }

        _createProgram() {
            const vertex = this._shader(
                this.gl.VERTEX_SHADER,
                "attribute vec3 a_position; attribute vec2 a_uv; uniform mat4 u_mvp; varying vec2 v_uv; void main(){ gl_Position=u_mvp*vec4(a_position,1.0); v_uv=a_uv; }"
            );
            const fragment = this._shader(
                this.gl.FRAGMENT_SHADER,
                "precision mediump float; uniform sampler2D u_texture; varying vec2 v_uv; void main(){ gl_FragColor=texture2D(u_texture,v_uv); }"
            );
            const program = this.gl.createProgram();
            this.gl.attachShader(program, vertex);
            this.gl.attachShader(program, fragment);
            this.gl.linkProgram(program);
            if (!this.gl.getProgramParameter(program, this.gl.LINK_STATUS)) {
                throw new Error(this.gl.getProgramInfoLog(program) || "WebGL program link failed");
            }
            return program;
        }

        _multiplyMatrices(a, b) {
            const output = new Float32Array(16);
            for (let column = 0; column < 4; column += 1) {
                for (let row = 0; row < 4; row += 1) {
                    let value = 0;
                    for (let index = 0; index < 4; index += 1) {
                        value += a[index * 4 + row] * b[column * 4 + index];
                    }
                    output[column * 4 + row] = value;
                }
            }
            return output;
        }

        _panelModelMatrix(viewerPose) {
            const translation = new Float32Array([
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                0, -0.05, -2.5, 1,
            ]);
            return this._multiplyMatrices(viewerPose.transform.matrix, translation);
        }

        _wrap(text, maxChars) {
            const words = String(text || "").split(/\s+/);
            const lines = [];
            let line = "";
            for (const word of words) {
                const candidate = line ? `${line} ${word}` : word;
                if (candidate.length > maxChars && line) {
                    lines.push(line);
                    line = word;
                } else {
                    line = candidate;
                }
            }
            if (line) lines.push(line);
            return lines.slice(0, 3);
        }

        _action(state) {
            if (state.phase === "MOVE_BUTTON_CHECK") return "HOLD ONE RIGHT BUTTON";
            if (state.phase === "READY") return "PRESS LEFT TRIGGER";
            if (state.phase === "HOLD_MOVE") return "KEEP RIGHT MOVE HELD";
            if (state.phase === "BASELINE" && state.test === "T0") return "MOVE RIGHT CONTROLLER SLOWLY";
            if (state.phase === "BASELINE") return "KEEP MOVE HELD AND WAIT";
            if (state.phase === "OCCLUDE") return "PUT RIGHT CONTROLLER BEHIND YOU";
            if (state.phase === "LOSS_DETECTED") return "KEEP MOVE HELD";
            if (state.phase === "RESTORE") return "BRING RIGHT CONTROLLER BACK";
            if (state.phase === "RECOVERY") return "KEEP MOVE HELD AND WAIT";
            if (state.phase === "COMPLETE") return "PRESS LEFT TRIGGER";
            if (state.phase === "INVALID") return "PRESS LEFT TRIGGER TO RETRY";
            if (state.phase === "FINAL") return "YOU MAY REMOVE THE HEADSET";
            return state.instruction;
        }

        update(state) {
            const signature = JSON.stringify(state);
            const now = nowMs();
            if (signature === this.lastSignature || now - this.lastDrawMs < 100) return;
            this.lastSignature = signature;
            this.lastDrawMs = now;
            const ctx = this.context;
            ctx.clearRect(0, 0, 1024, 1024);
            ctx.fillStyle = "rgba(0, 0, 0, 0.88)";
            ctx.fillRect(12, 12, 1000, 1000);
            ctx.strokeStyle = state.move ? "#62ffab" : "#ffd45c";
            ctx.lineWidth = 12;
            ctx.strokeRect(18, 18, 988, 988);
            ctx.fillStyle = "#62ffab";
            ctx.font = "bold 38px sans-serif";
            ctx.fillText("SPES QUEST VALIDATION", 52, 68);
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 44px sans-serif";
            ctx.fillText(`${state.test}  ${state.trial}   |   ${state.phase}`, 52, 132);

            ctx.fillStyle = "#9bd8ff";
            ctx.font = "bold 32px sans-serif";
            ctx.fillText("DO THIS NOW", 52, 196);
            ctx.fillStyle = state.phase === "INVALID" ? "#ff756d" : "#ffffff";
            ctx.font = "bold 76px sans-serif";
            let actionY = 286;
            for (const line of this._wrap(this._action(state), 21)) {
                ctx.fillText(line, 52, actionY);
                actionY += 88;
            }
            if (["OCCLUDE", "LOSS_DETECTED", "RESTORE", "RECOVERY"].includes(state.phase)) {
                ctx.fillStyle = "#ffd45c";
                ctx.font = "bold 36px sans-serif";
                ctx.fillText("DO NOT RELEASE OR RE-PRESS MOVE", 52, 485);
            }

            ctx.fillStyle = state.move ? "#62ffab" : "#ff756d";
            ctx.font = "bold 58px sans-serif";
            ctx.fillText(`MOVE: ${state.move ? "TRUE" : "FALSE"}`, 52, 580);
            ctx.fillStyle = state.rightInput === "PRESENT" ? "#62ffab" : "#ff756d";
            ctx.fillText(`RIGHT: ${state.rightInput}`, 510, 580);

            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 33px sans-serif";
            ctx.fillText(`SERVER ${state.server}   WSS ${state.wss}`, 52, 660);
            ctx.fillText(`POSE ${state.controllerPose}   EMULATED ${state.emulated}`, 52, 720);
            ctx.fillText(`SOURCE ${state.source}`, 52, 780);
            ctx.fillText(`PACKET ${state.packet}   ACK ${state.ack}`, 52, 840);
            ctx.fillText(`CORRELATION ${state.correlation}`, 52, 895);
            ctx.fillStyle = "#ffd45c";
            ctx.font = "bold 24px sans-serif";
            const eventText = `LAST: ${state.event || "-"}`;
            ctx.fillText(eventText.slice(0, 70), 52, 955);
            this.dirty = true;
        }

        render(frame, referenceSpace) {
            const gl = this.gl;
            const baseLayer = this.session.renderState && this.session.renderState.baseLayer;
            if (!baseLayer) return;
            const viewerPose = frame.getViewerPose(referenceSpace);
            if (!viewerPose || !viewerPose.transform || !viewerPose.transform.matrix) return;
            const panelModel = this._panelModelMatrix(viewerPose);
            gl.bindFramebuffer(gl.FRAMEBUFFER, baseLayer.framebuffer);
            if (this.dirty) {
                gl.bindTexture(gl.TEXTURE_2D, this.texture);
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, this.canvas);
                this.dirty = false;
            }
            gl.useProgram(this.program);
            gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
            gl.enableVertexAttribArray(this.positionLocation);
            gl.vertexAttribPointer(this.positionLocation, 3, gl.FLOAT, false, 20, 0);
            gl.enableVertexAttribArray(this.uvLocation);
            gl.vertexAttribPointer(this.uvLocation, 2, gl.FLOAT, false, 20, 12);
            gl.activeTexture(gl.TEXTURE0);
            gl.bindTexture(gl.TEXTURE_2D, this.texture);
            gl.uniform1i(this.textureLocation, 0);
            gl.disable(gl.DEPTH_TEST);
            gl.enable(gl.BLEND);
            gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
            for (const view of viewerPose.views) {
                const viewport = baseLayer.getViewport(view);
                if (!viewport || !view.projectionMatrix || !view.transform || !view.transform.inverse) continue;
                const viewModel = this._multiplyMatrices(view.transform.inverse.matrix, panelModel);
                const mvp = this._multiplyMatrices(view.projectionMatrix, viewModel);
                gl.uniformMatrix4fv(this.mvpLocation, false, mvp);
                gl.viewport(viewport.x, viewport.y, viewport.width, viewport.height);
                gl.drawArrays(gl.TRIANGLES, 0, 6);
            }
            gl.disable(gl.BLEND);
        }
    }

    class QuestExperimentOperator {
        constructor(options = {}) {
            this.config = { ...CONFIG, ...(options.config || {}) };
            this.socketFactory = options.socketFactory || ((url) => new WebSocket(url));
            this.sideband = null;
            this.sidebandReconnectTimer = null;
            this.pendingEvents = [];
            this.sequence = 0;
            this.session = null;
            this.sessionVisibility = null;
            this.documentVisibility = document.visibilityState || "visible";
            this.productionConnected = false;
            this.sidebandConnected = false;
            this.domOverlayType = "NOT_CHECKED";
            this.speechSupported = Boolean(global.speechSynthesis && global.SpeechSynthesisUtterance);
            this.webAudioSupported = Boolean(global.AudioContext || global.webkitAudioContext);
            this.audioContext = null;
            this.xrHudRenderer = null;
            this.xrHudFailureLogged = false;
            this.lastMoveReminderMs = Number.NEGATIVE_INFINITY;
            this.leftPressStartMs = null;
            this.moveTrueSinceMs = null;
            this.test = "T0";
            this.trial = 0;
            this.validTrials = 0;
            this.phase = "MOVE_BUTTON_CHECK";
            this.phaseStartedMs = nowMs();
            this.instruction = "PRESS/HOLD THE RIGHT BUTTON UNTIL MOVE = TRUE";
            this.lastEvent = "Operator initialized";
            this.lastObservation = null;
            this.lastRawSampleMs = Number.NEGATIVE_INFINITY;
            this.lastViewerPoseExists = false;
            this.lastControllerEmulated = null;
            this.latestAck = {
                server_update_index: null,
                last_callback_time: null,
                callback_emitted: null,
                callback_count: 0,
                jump_reject_count: 0,
                target_delta: null,
                correlation_status: "NO_ACK",
            };
            this.currentTrial = null;
            this.t0 = null;
            this.invalidUntilMs = null;
            this.counts = {
                HW_EMULATED_CONTINUES: 0,
                HW_VIEWER_FALLBACK_CONTINUES: 0,
                HW_FAIL_CLOSED: 0,
                HW_NO_LOSS_OBSERVED: 0,
                RECOVERY_AUTO: 0,
            };
            this._installHud();
            this._installDocumentVisibilityObserver();
            this._render();
        }

        _installHud() {
            const root = document.querySelector("#app");
            if (!root || !document.createElement) return;
            const style = document.createElement("style");
            style.textContent = `
                #spes-quest-hud { position: fixed; inset: 3vh 3vw auto 3vw; z-index: 2147483647;
                    padding: 18px 22px; color: #fff; background: rgba(0,0,0,.78); border: 3px solid #51e39b;
                    border-radius: 14px; font: 700 20px/1.25 system-ui, sans-serif; pointer-events: none; }
                #spes-quest-hud .title { color: #51e39b; font-size: 28px; letter-spacing: 1px; }
                #spes-quest-hud .action { margin: 14px 0; padding: 14px; color: #fff; background: #173c2b;
                    border-radius: 10px; font-size: 32px; text-align: center; }
                #spes-quest-hud .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 22px; }
                #spes-quest-hud .bad { color: #ff796f; } #spes-quest-hud .good { color: #70ffad; }
                #spes-quest-hud .event { margin-top: 10px; color: #ffd76b; font-size: 17px; }
            `;
            if (document.head && document.head.appendChild) document.head.appendChild(style);
            const hud = document.createElement("div");
            hud.id = "spes-quest-hud";
            hud.innerHTML = `
                <div class="title">SPES QUEST VALIDATION</div>
                <div class="action" data-field="instruction"></div>
                <div class="grid">
                    <div data-field="server"></div><div data-field="wss"></div>
                    <div data-field="test"></div><div data-field="trial"></div>
                    <div data-field="phase"></div><div data-field="right_input"></div>
                    <div data-field="controller_pose"></div><div data-field="emulated"></div>
                    <div data-field="viewer_pose"></div><div data-field="source"></div>
                    <div data-field="move"></div><div data-field="packet"></div>
                    <div data-field="ack"></div><div data-field="correlation"></div>
                </div>
                <div class="event" data-field="event"></div>`;
            root.appendChild(hud);
            this.hud = hud;
        }

        _installDocumentVisibilityObserver() {
            if (!document.addEventListener) return;
            document.addEventListener("visibilitychange", () => {
                this.documentVisibility = document.visibilityState || null;
                this._event("document_visibilitychange", {
                    document_visibility_state: this.documentVisibility,
                });
                if (this.documentVisibility === "hidden") this._invalidateFocus("DOCUMENT_HIDDEN");
            });
        }

        _field(name, value, good = null) {
            if (!this.hud || !this.hud.querySelector) return;
            const node = this.hud.querySelector(`[data-field="${name}"]`);
            if (!node) return;
            node.textContent = value;
            node.className = good === true ? "good" : good === false ? "bad" : "";
        }

        _render() {
            const o = this.lastObservation || {};
            const emulated = o.controllerPose
                ? String(Boolean(o.controllerPose.emulatedPosition)).toUpperCase()
                : "N/A";
            const viewerExists = o.viewerPose
                ? true
                : this.lastViewerPoseExists;
            this._field("instruction", this.instruction);
            this._field("server", `SERVER: ${this.productionConnected ? "CONNECTED" : "DISCONNECTED"}`, this.productionConnected);
            this._field("wss", `WSS: ${this.sidebandConnected ? "CONNECTED" : "DISCONNECTED"}`, this.sidebandConnected);
            this._field("test", `TEST: ${this.test}`);
            this._field("trial", `TRIAL: ${this.test === "T1" ? `${Math.min(this.validTrials + 1, 5)} / 5` : "-"}`);
            this._field("phase", `PHASE: ${this.phase}`);
            this._field("right_input", `RIGHT INPUT: ${o.rightControllerInputSourcePresent ? "PRESENT" : "ABSENT"}`, Boolean(o.rightControllerInputSourcePresent));
            this._field("controller_pose", `CONTROLLER POSE: ${o.controllerPose ? "YES" : "NO"}`, Boolean(o.controllerPose));
            this._field("emulated", `CONTROLLER EMULATED: ${emulated}`);
            this._field("viewer_pose", `VIEWER POSE: ${viewerExists ? "YES" : "NO"}`, viewerExists);
            this._field("source", `SELECTED SOURCE: ${o.selectedSource || "NONE"}`);
            this._field("move", `MOVE: ${o.move ? "TRUE" : "FALSE"}`, Boolean(o.move));
            this._field("packet", `CONTROL PACKET INDEX: ${o.controlPacketIndex ?? 0}`);
            this._field("ack", `SERVER UPDATE/ACK INDEX: ${this.latestAck.server_update_index ?? "-"}`);
            this._field("correlation", `CORRELATION: ${this.latestAck.correlation_status || "NO_ACK"}`);
            this._field("event", `LAST EVENT: ${this.lastEvent}`);
            if (this.xrHudRenderer) {
                this.xrHudRenderer.update({
                    instruction: this.instruction,
                    server: this.productionConnected ? "CONNECTED" : "DISCONNECTED",
                    wss: this.sidebandConnected ? "CONNECTED" : "DISCONNECTED",
                    test: this.test,
                    trial: this.test === "T1" ? `${Math.min(this.validTrials + 1, 5)}/5` : "-",
                    phase: this.phase,
                    rightInput: o.rightControllerInputSourcePresent ? "PRESENT" : "ABSENT",
                    controllerPose: o.controllerPose ? "YES" : "NO",
                    emulated,
                    viewerPose: viewerExists ? "YES" : "NO",
                    source: o.selectedSource || "NONE",
                    move: Boolean(o.move),
                    packet: o.controlPacketIndex ?? 0,
                    ack: this.latestAck.server_update_index ?? "-",
                    correlation: this.latestAck.correlation_status || "NO_ACK",
                    event: this.lastEvent,
                });
            }
        }

        _ensureAudio() {
            if (!this.webAudioSupported) return;
            if (this.audioContext) {
                if (this.audioContext.state === "suspended" && this.audioContext.resume) {
                    this.audioContext.resume().catch(() => {});
                }
                return;
            }
            try {
                const AudioContextClass = global.AudioContext || global.webkitAudioContext;
                this.audioContext = new AudioContextClass();
                if (this.audioContext.resume) this.audioContext.resume().catch(() => {});
            } catch (error) {
                this.webAudioSupported = false;
                this._event("audio_init_failed", { error: String(error) });
            }
        }

        _beep(pattern = [0.08]) {
            this._ensureAudio();
            if (!this.audioContext) return;
            const play = () => {
                let offset = 0;
                for (const duration of pattern) {
                    const oscillator = this.audioContext.createOscillator();
                    const gain = this.audioContext.createGain();
                    oscillator.frequency.value = 660 + offset * 120;
                    gain.gain.value = 0.08;
                    oscillator.connect(gain);
                    gain.connect(this.audioContext.destination);
                    const start = this.audioContext.currentTime + offset;
                    oscillator.start(start);
                    oscillator.stop(start + duration);
                    offset += duration + 0.08;
                }
            };
            try {
                if (this.audioContext.state === "suspended" && this.audioContext.resume) {
                    this.audioContext.resume().then(play).catch((error) => {
                        this._event("audio_resume_failed", { error: String(error) });
                    });
                } else {
                    play();
                }
            } catch (error) {
                this._event("audio_beep_failed", { error: String(error) });
            }
        }

        _announce(text, pattern = [0.08]) {
            if (this.speechSupported) {
                try {
                    const utterance = new global.SpeechSynthesisUtterance(text);
                    utterance.rate = 1.05;
                    utterance.onerror = () => this._beep(pattern);
                    global.speechSynthesis.speak(utterance);
                    return;
                } catch (error) {
                    this.speechSupported = false;
                }
            }
            this._beep(pattern);
        }

        _connectSideband() {
            if (this.sideband && [0, 1].includes(this.sideband.readyState)) return;
            try {
                const socket = this.socketFactory(websocketUrl("/experiment"));
                this.sideband = socket;
                socket.onopen = () => {
                    this.sidebandConnected = true;
                    this.lastEvent = "Experiment WSS connected";
                    this._flushEvents();
                    this._event("experiment_wss_open");
                    this._render();
                };
                socket.onclose = () => {
                    this.sidebandConnected = false;
                    this.lastEvent = "Experiment WSS disconnected";
                    this._event("experiment_wss_close");
                    this._render();
                    if (global.setTimeout) {
                        this.sidebandReconnectTimer = global.setTimeout(() => this._connectSideband(), 1000);
                    }
                };
                socket.onerror = () => {
                    this.sidebandConnected = false;
                    this.lastEvent = "Experiment WSS error";
                    this._event("experiment_wss_error");
                    this._render();
                };
                socket.onmessage = (event) => this._handleSidebandMessage(event.data);
            } catch (error) {
                this.lastEvent = `Experiment WSS unavailable: ${error}`;
            }
        }

        _flushEvents() {
            if (!this.sidebandConnected || !this.sideband || this.sideband.readyState !== WebSocket.OPEN) return;
            for (const record of this.pendingEvents.splice(0)) {
                this.sideband.send(JSON.stringify({ type: "experiment_event", data: record }));
            }
        }

        _event(eventType, details = {}) {
            const o = this.lastObservation || {};
            const record = {
                schema: "spes-quest-operator-v1",
                operator_event_sequence: ++this.sequence,
                event_type: eventType,
                sample_kind: eventType === "frame_sample" ? "HIGH_FREQUENCY_SAMPLE" : "SEMANTIC_EVENT",
                wall_timestamp: new Date().toISOString(),
                monotonic_timestamp_ms: finite(nowMs()),
                xr_frame_time: finite(o.xrFrameTime),
                test: this.test,
                trial: this.test === "T1" ? this.validTrials + 1 : this.trial,
                phase: this.phase,
                right_input_exists: Boolean(o.rightControllerInputSourcePresent),
                controller_pose_exists: Boolean(o.controllerPose),
                controller_emulated_position: o.controllerPose ? Boolean(o.controllerPose.emulatedPosition) : null,
                controller_pose: o.controllerPose ? snapshotTransform(o.controllerPose) : null,
                viewer_pose_exists: o.viewerPose ? true : this.lastViewerPoseExists,
                viewer_pose: o.viewerPose && o.viewerPose.views && o.viewerPose.views[0]
                    ? snapshotTransform(o.viewerPose.views[0].transform)
                    : null,
                selected_source: o.selectedSource || "NONE",
                move: Boolean(o.move),
                production_wss_state: this.productionConnected ? "CONNECTED" : "DISCONNECTED",
                experiment_wss_state: this.sidebandConnected ? "CONNECTED" : "DISCONNECTED",
                control_packet_index: o.controlPacketIndex ?? 0,
                server_update_index: this.latestAck.server_update_index,
                server_last_callback_time: this.latestAck.last_callback_time,
                target_delta: this.latestAck.target_delta,
                jump_reject: Boolean(this.latestAck.jump_reject),
                xr_visibility_state: this.sessionVisibility,
                document_visibility_state: this.documentVisibility,
                classification: this.currentTrial && this.currentTrial.classification,
                ...details,
            };
            if (this.sidebandConnected && this.sideband && this.sideband.readyState === WebSocket.OPEN) {
                try {
                    this.sideband.send(JSON.stringify({ type: "experiment_event", data: record }));
                } catch (_) {
                    this.pendingEvents.push(record);
                }
            } else {
                this.pendingEvents.push(record);
                if (this.pendingEvents.length > 512) this.pendingEvents.shift();
            }
            return record;
        }

        _handleSidebandMessage(payload) {
            let message;
            try {
                message = JSON.parse(payload);
            } catch (_) {
                return;
            }
            if (message.type === "server_ack") {
                const previousUpdate = this.latestAck.server_update_index;
                this.latestAck = {
                    ...this.latestAck,
                    ...message,
                    callback_count: Number.isFinite(message.callback_count)
                        ? message.callback_count
                        : this.latestAck.callback_count + (message.callback_emitted ? 1 : 0),
                    jump_reject_count: this.latestAck.jump_reject_count + (message.jump_reject ? 1 : 0),
                    correlation_status: message.server_update_index === (this.lastObservation && this.lastObservation.controlPacketIndex)
                        ? "MATCH_LATEST_PACKET"
                        : previousUpdate === message.server_update_index
                            ? "DUPLICATE_ACK"
                            : "ACK_PROGRESSING",
                };
            } else if (message.type === "experiment_hello") {
                this.lastEvent = `Server ready: ${message.run_id || "unknown run"}`;
            }
            this._render();
        }

        onProductionWebSocket(state, details = {}) {
            this.productionConnected = state === "open";
            this.lastEvent = `Production WSS ${state}`;
            if (state === "open") this._connectSideband();
            this._event(`production_wss_${state}`, details);
            this._render();
        }

        onSessionStarted(session) {
            this.session = session;
            this.sessionVisibility = session.visibilityState || null;
            this.domOverlayType = session.domOverlayState && session.domOverlayState.type
                ? session.domOverlayState.type
                : "UNAVAILABLE";
            this._ensureAudio();
            const selectStart = (event) => {
                if (!event.inputSource || event.inputSource.handedness !== "left") return;
                this._ensureAudio();
                this._beep([0.04]);
                this.leftPressStartMs = nowMs();
                this._event("left_selectstart");
            };
            const selectEnd = (event) => {
                if (!event.inputSource || event.inputSource.handedness !== "left") return;
                const duration = this.leftPressStartMs === null ? 0 : nowMs() - this.leftPressStartMs;
                this.leftPressStartMs = null;
                this._event("left_selectend", { press_duration_ms: finite(duration) });
                if (duration >= 2000) this._longPress();
                else this._shortPress();
            };
            session.addEventListener("selectstart", selectStart);
            session.addEventListener("selectend", selectEnd);
            session.addEventListener("visibilitychange", () => {
                this.sessionVisibility = session.visibilityState || null;
                this._event("xr_visibilitychange", { xr_visibility_state: this.sessionVisibility });
                if (this.sessionVisibility && this.sessionVisibility !== "visible") {
                    this._invalidateFocus(`XR_${this.sessionVisibility}`);
                }
                this._render();
            });
            session.addEventListener("inputsourceschange", (event) => {
                this._event("inputsourceschange", {
                    added_count: event.added ? event.added.length : null,
                    removed_count: event.removed ? event.removed.length : null,
                });
            });
            this._connectSideband();
            this._event("operator_preflight", {
                dom_overlay_type: this.domOverlayType,
                dom_overlay_available: this.domOverlayType !== "UNAVAILABLE",
                speech_synthesis_available: this.speechSupported,
                web_audio_available: this.webAudioSupported,
                left_controller_events_installed: true,
            });
            this._announce("Experiment ready", [0.08, 0.08]);
            this._render();
        }

        attachXRRenderer(gl, session) {
            if (this.domOverlayType !== "UNAVAILABLE") {
                this._event("xr_hud_renderer_skipped", { reason: "DOM_OVERLAY_AVAILABLE" });
                return false;
            }
            try {
                this.xrHudRenderer = new XRHudRenderer(gl, session);
                this._event("xr_hud_renderer_ready", {
                    renderer: "WEBGL_CLIPSPACE_CANVAS_TEXTURE",
                    framework: "NONE",
                });
                this._render();
                return true;
            } catch (error) {
                this.xrHudRenderer = null;
                this._event("xr_hud_renderer_failed", { error: String(error) });
                return false;
            }
        }

        renderXRFrame(frame, referenceSpace) {
            if (!this.xrHudRenderer) return;
            try {
                this.xrHudRenderer.render(frame, referenceSpace);
            } catch (error) {
                if (!this.xrHudFailureLogged) {
                    this.xrHudFailureLogged = true;
                    this._event("xr_hud_render_failed", { error: String(error) });
                }
            }
        }

        onSessionEnded() {
            this._event("xr_session_end");
            this.session = null;
        }

        onInputSourcesChange(details = {}) {
            this._event("inputsourceschange_observed", details);
        }

        _setPhase(phase, instruction, announcement = null, eventType = "phase_transition") {
            const previous = this.phase;
            this.phase = phase;
            this.phaseStartedMs = nowMs();
            this.instruction = instruction;
            this.lastEvent = `${previous} -> ${phase}`;
            this._event(eventType, { previous_phase: previous, next_phase: phase, instruction });
            if (announcement) this._announce(announcement);
            this._render();
        }

        _shortPress() {
            if (this.phase === "MOVE_BUTTON_CHECK") {
                this.lastEvent = "Right move is not confirmed";
                this._event("left_press_blocked_move_not_confirmed");
                this._announce("Hold the right move button first", [0.05, 0.05, 0.22]);
                this._render();
            } else if (this.phase === "READY" && this.test === "T0") {
                this.t0 = null;
                this.moveTrueSinceMs = null;
                this._setPhase("HOLD_MOVE", "HOLD RIGHT MOVE BUTTON", "Hold move");
            } else if (this.phase === "COMPLETE" && this.test === "T0") {
                this.test = "T1";
                this.trial = 1;
                this._setPhase("READY", "T1 TRIAL 1/5 - PRESS LEFT TRIGGER");
            } else if (this.phase === "READY" && this.test === "T1") {
                this.currentTrial = this._newTrial();
                this.moveTrueSinceMs = null;
                this._setPhase("HOLD_MOVE", "HOLD RIGHT MOVE BUTTON", "Hold move");
            } else if (this.phase === "COMPLETE" && this.test === "T1") {
                if (this.validTrials >= 5) {
                    this.test = "T4";
                    this._setPhase("READY", "T4 OPTIONAL - SHORT PRESS TO RUN, LONG PRESS TO SKIP");
                } else {
                    this.trial = this.validTrials + 1;
                    this._setPhase("READY", `T1 TRIAL ${this.trial}/5 - PRESS LEFT TRIGGER`);
                }
            } else if (this.phase === "INVALID") {
                this.invalidUntilMs = nowMs();
            } else if (this.phase === "READY" && this.test === "T4") {
                this.currentTrial = this._newTrial();
                this._setPhase("OCCLUDE", "OPTIONAL: DISCONNECT RIGHT CONTROLLER, THEN RESTORE", "Optional disconnect test");
            }
        }

        _longPress() {
            if (this.test === "T4" && this.phase === "READY") {
                this._event("t4_skipped");
                this._finishExperiment();
                return;
            }
            if (["FINAL", "MOVE_BUTTON_CHECK"].includes(this.phase)) return;
            this._invalidate("INVALID_MANUAL_ABORT", "Manual abort. Repeat trial.", "Trial aborted");
        }

        _newTrial() {
            return {
                number: this.validTrials + 1,
                baseline_controller_emulated: null,
                loss_event: null,
                loss_detected_ms: null,
                loss_control_index: null,
                loss_server_index: null,
                loss_callback_count: null,
                loss_jump_reject_count_start: null,
                recovery_control_index: null,
                recovery_server_index: null,
                recovery_callback_count: null,
                loss_sample_count: 0,
                viewer_fallback_sample_count: 0,
                move_ever_false: false,
                classification: null,
                recovery_classification: null,
            };
        }

        _isCriticalPhase() {
            return ["OCCLUDE", "LOSS_DETECTED", "RESTORE", "RECOVERY"].includes(this.phase);
        }

        _invalidateFocus(reason) {
            if (this._isCriticalPhase()) {
                this._invalidate("INVALID_SESSION_FOCUS", "Session focus changed. Repeat trial.", "Trial invalid");
                this._event("focus_invalid_reason", { reason });
            }
        }

        _invalidate(classification, instruction, announcement) {
            if (this.currentTrial) this.currentTrial.classification = classification;
            this._event("trial_invalid", { classification });
            this.invalidUntilMs = nowMs() + this.config.invalidDisplayMs;
            this._setPhase("INVALID", instruction, announcement, "invalid_transition");
        }

        _hardBaselineFailures(o) {
            const failures = [];
            if (!o.rightControllerInputSourcePresent) failures.push("RIGHT INPUT ABSENT");
            if (!o.controllerPose) failures.push("CONTROLLER POSE NO");
            if (o.selectedSource !== "CONTROLLER") failures.push("SOURCE NOT CONTROLLER");
            if (!o.move) failures.push("MOVE FALSE");
            if (!this.productionConnected) failures.push("SERVER DISCONNECTED");
            if (!this.sidebandConnected) failures.push("ACK WSS DISCONNECTED");
            return failures;
        }

        _startBaseline(o) {
            if (this.test === "T0") {
                this.t0 = {
                    start_ms: nowMs(),
                    start_server_index: this.latestAck.server_update_index || 0,
                    start_control_index: o.controlPacketIndex || 0,
                    saw_non_emulated: false,
                };
                this._setPhase("BASELINE", "MOVE CONTROLLER SLOWLY LEFT/RIGHT/FORWARD/BACK", "Baseline");
            } else {
                this.currentTrial.baseline_controller_emulated = Boolean(o.controllerPose && o.controllerPose.emulatedPosition);
                this.currentTrial.baseline_control_index = o.controlPacketIndex || 0;
                this.currentTrial.baseline_server_index = this.latestAck.server_update_index || 0;
                this.currentTrial.baseline_callback_count = this.latestAck.callback_count;
                this._setPhase("BASELINE", "KEEP RIGHT MOVE PRESSED - BASELINE", "Baseline");
            }
        }

        _handleMoveCheck(o, now) {
            if (o.move && o.rightControllerInputSourcePresent && o.controllerPose
                && o.selectedSource === "CONTROLLER") {
                if (this.moveTrueSinceMs === null) this.moveTrueSinceMs = now;
                if (now - this.moveTrueSinceMs >= this.config.stableMoveMs) {
                    this._event("move_button_confirmed", { stable_ms: now - this.moveTrueSinceMs });
                    this._announce("Move button confirmed", [0.15, 0.06]);
                    this._setPhase("READY", "PRESS LEFT TRIGGER TO BEGIN T0");
                }
            } else {
                this.moveTrueSinceMs = null;
            }
        }

        _handleHoldMove(o, now) {
            const failures = this._hardBaselineFailures(o);
            if (failures.length > 0) {
                this.moveTrueSinceMs = null;
                this.instruction = failures.join(" | ");
                return;
            }
            if (o.controllerPose && o.controllerPose.emulatedPosition) {
                this.moveTrueSinceMs = null;
                this.instruction = "RESTORE NORMAL RIGHT CONTROLLER TRACKING";
                return;
            }
            if (this.moveTrueSinceMs === null) this.moveTrueSinceMs = now;
            if (now - this.moveTrueSinceMs >= this.config.stableMoveMs) this._startBaseline(o);
        }

        _handleT0(o, now) {
            const failures = this._hardBaselineFailures(o);
            if (failures.length > 0) {
                this.t0.start_ms = now;
                this.t0.start_server_index = this.latestAck.server_update_index || 0;
                this.t0.start_control_index = o.controlPacketIndex || 0;
                this.instruction = `T0 WAIT: ${failures.join(" | ")}`;
                return;
            }
            if (o.controllerPose && !o.controllerPose.emulatedPosition) this.t0.saw_non_emulated = true;
            if (now - this.t0.start_ms < this.config.t0DurationMs) return;
            const serverProgress = (this.latestAck.server_update_index || 0) > this.t0.start_server_index;
            const packetProgress = (o.controlPacketIndex || 0) > this.t0.start_control_index;
            if (!serverProgress || !packetProgress) {
                this.t0.start_ms = now;
                this.instruction = `T0 WAIT: ${!packetProgress ? "CONTROL PACKET NOT PROGRESSING" : "SERVER ACK NOT PROGRESSING"}`;
                return;
            }
            this._event("t0_complete", {
                result: "PASS",
                saw_controller_emulated_false: this.t0.saw_non_emulated,
                control_packet_progress: (o.controlPacketIndex || 0) - this.t0.start_control_index,
                server_update_progress: (this.latestAck.server_update_index || 0) - this.t0.start_server_index,
            });
            this._setPhase("COMPLETE", "T0 PASS - PRESS LEFT TRIGGER FOR T1", "Trial complete");
        }

        _handleT1Baseline(o, now) {
            const failures = this._hardBaselineFailures(o);
            if (failures.length || (o.controllerPose && o.controllerPose.emulatedPosition)) {
                this.phaseStartedMs = now;
                this.instruction = failures.length ? failures.join(" | ") : "RESTORE NORMAL TRACKING";
                return;
            }
            if (now - this.phaseStartedMs >= this.config.baselineDurationMs) {
                this.currentTrial.occlude_control_index = o.controlPacketIndex || 0;
                this.currentTrial.occlude_server_index = this.latestAck.server_update_index || 0;
                this.currentTrial.occlude_callback_count = this.latestAck.callback_count;
                this._setPhase("OCCLUDE", "OCCLUDE RIGHT CONTROLLER - KEEP MOVE PRESSED", "Occlude right controller");
            }
        }

        _detectLoss(o, now) {
            if (this.currentTrial.loss_event) return;
            let event = null;
            if (!o.rightControllerInputSourcePresent) {
                event = "INPUT_SOURCE_LOST";
            } else if (o.controllerPose && o.controllerPose.emulatedPosition && this.lastControllerEmulated === false) {
                event = "EMULATED_TRACKING_LOSS";
            } else if (!o.controllerPose && o.viewerPose && o.selectedSource === "VIEWER_FALLBACK") {
                event = "VIEWER_FALLBACK";
            }
            if (!event) return;
            Object.assign(this.currentTrial, {
                loss_event: event,
                loss_detected_ms: now,
                loss_control_index: o.controlPacketIndex || 0,
                loss_server_index: this.latestAck.server_update_index || 0,
                loss_callback_count: this.latestAck.callback_count,
                loss_jump_reject_count_start: this.latestAck.jump_reject_count,
            });
            this.lastEvent = event;
            this._event("tracking_change_detected", { loss_event: event });
            this._announce("Tracking change detected. Keep move pressed", [0.08, 0.08, 0.15]);
            this._setPhase("LOSS_DETECTED", "TRACKING CHANGE DETECTED - KEEP MOVE PRESSED");
        }

        _handleOcclude(o, now) {
            this._detectLoss(o, now);
            if (o.controllerPose && o.controllerPose.emulatedPosition) this.currentTrial.loss_sample_count += 1;
            if (!o.controllerPose && o.viewerPose && o.selectedSource === "VIEWER_FALLBACK") {
                this.currentTrial.viewer_fallback_sample_count += 1;
            }
            const enoughAfterLoss = this.currentTrial.loss_detected_ms !== null
                && now - this.currentTrial.loss_detected_ms >= this.config.postLossObserveMs;
            const timeout = now - this.phaseStartedMs >= this.config.occlusionMaxMs;
            if (!enoughAfterLoss && !timeout) return;
            if (!this.currentTrial.loss_event) {
                this.currentTrial.loss_event = "NO_LOSS_STATE_OBSERVED";
                this.currentTrial.loss_control_index = o.controlPacketIndex || 0;
                this.currentTrial.loss_server_index = this.latestAck.server_update_index || 0;
                this.currentTrial.loss_callback_count = this.latestAck.callback_count;
                this.currentTrial.loss_jump_reject_count_start = this.latestAck.jump_reject_count;
                this._event("occlusion_timeout", { loss_event: "NO_LOSS_STATE_OBSERVED" });
            }
            this._setPhase("RESTORE", "RESTORE RIGHT CONTROLLER - DO NOT RE-PRESS MOVE", "Restore right controller");
        }

        _recovered(o) {
            return Boolean(
                o.rightControllerInputSourcePresent
                && o.controllerPose
                && !o.controllerPose.emulatedPosition
                && o.selectedSource === "CONTROLLER"
            );
        }

        _handleRestore(o) {
            if (!this._recovered(o)) return;
            Object.assign(this.currentTrial, {
                recovery_control_index: o.controlPacketIndex || 0,
                recovery_server_index: this.latestAck.server_update_index || 0,
                recovery_callback_count: this.latestAck.callback_count,
            });
            this._event("tracking_reacquired", {
                first_reacquired_pose: snapshotTransform(o.controllerPose),
            });
            this._setPhase("RECOVERY", "RECOVERY - KEEP MOVE PRESSED - DO NOT RE-PRESS", "Recovery");
        }

        _classifyTrial(o) {
            const trial = this.currentTrial;
            const packetContinues = (o.controlPacketIndex || 0) > (trial.loss_control_index || 0);
            const serverContinues = (this.latestAck.server_update_index || 0) > (trial.loss_server_index || 0);
            const callbackContinues = this.latestAck.callback_count > (trial.loss_callback_count || 0);
            if (trial.loss_event === "EMULATED_TRACKING_LOSS" && trial.loss_sample_count > 0
                && packetContinues && serverContinues && callbackContinues) {
                trial.classification = "HW_EMULATED_CONTINUES";
            } else if (trial.loss_event === "VIEWER_FALLBACK" && trial.viewer_fallback_sample_count > 0
                && packetContinues && serverContinues && callbackContinues) {
                trial.classification = "HW_VIEWER_FALLBACK_CONTINUES";
            } else if (["EMULATED_TRACKING_LOSS", "VIEWER_FALLBACK", "INPUT_SOURCE_LOST"].includes(trial.loss_event)
                && (!packetContinues || !serverContinues || !callbackContinues)) {
                trial.classification = "HW_FAIL_CLOSED";
            } else {
                trial.classification = "HW_NO_LOSS_OBSERVED";
            }
            // Recovery evidence starts at the semantic-loss boundary. Counting from
            // trial creation lets an unrelated baseline jump reject contaminate the
            // recovery classification (the hardware trial-1 false positive).
            const jumpCountAtLoss = Number.isFinite(trial.loss_jump_reject_count_start)
                ? trial.loss_jump_reject_count_start
                : this.latestAck.jump_reject_count;
            const jumps = Math.max(0, this.latestAck.jump_reject_count - jumpCountAtLoss);
            const callbacksDuringLoss = (trial.recovery_callback_count || 0) > (trial.loss_callback_count || 0);
            const callbacksAfterRecovery = this.latestAck.callback_count > (trial.recovery_callback_count || 0);
            if (!callbacksAfterRecovery && !callbacksDuringLoss) {
                trial.recovery_classification = "RECOVERY_FAIL_CLOSED";
            } else if (jumps > 0 && callbacksAfterRecovery) {
                trial.recovery_classification = "RECOVERY_JUMP_REJECT_THEN_REANCHOR";
            } else if (!callbacksDuringLoss && callbacksAfterRecovery) {
                trial.recovery_classification = "RECOVERY_AUTO_REARM";
            } else {
                trial.recovery_classification = "RECOVERY_CONTINUOUS";
            }
            this.counts[trial.classification] += 1;
            if (["RECOVERY_AUTO_REARM", "RECOVERY_CONTINUOUS", "RECOVERY_JUMP_REJECT_THEN_REANCHOR"].includes(trial.recovery_classification)) {
                this.counts.RECOVERY_AUTO += 1;
            }
            return { packetContinues, serverContinues, callbackContinues, jumps };
        }

        _handleRecovery(o, now) {
            if (now - this.phaseStartedMs < this.config.recoveryDurationMs) return;
            const evidence = this._classifyTrial(o);
            this.validTrials += 1;
            this.trial = this.validTrials;
            this._event("trial_complete", {
                valid_trial_number: this.validTrials,
                loss_behavior: this.currentTrial.loss_event,
                classification: this.currentTrial.classification,
                recovery_classification: this.currentTrial.recovery_classification,
                move_ever_false: this.currentTrial.move_ever_false,
                ...evidence,
            });
            const instruction = this.validTrials >= 5
                ? "T1 COMPLETE - PRESS LEFT TRIGGER FOR OPTIONAL T4"
                : `TRIAL ${this.validTrials} COMPLETE - PRESS LEFT TRIGGER`;
            this._setPhase("COMPLETE", instruction, "Trial complete");
        }

        _handleT4(o, now) {
            if (this.phase === "OCCLUDE") {
                if (!o.rightControllerInputSourcePresent) {
                    this._event("t4_input_source_lost", {
                        selected_source: o.selectedSource,
                        move: Boolean(o.move),
                    });
                    this._setPhase("RESTORE", "RESTORE RIGHT CONTROLLER", "Restore right controller");
                } else if (now - this.phaseStartedMs >= 10000) {
                    this._event("t4_complete", { classification: "HW_T4_NO_DISCONNECT_OBSERVED" });
                    this._finishExperiment();
                }
            } else if (this.phase === "RESTORE" && this._recovered(o)) {
                this._event("t4_complete", { classification: "HW_T4_DISCONNECT_RECOVERED" });
                this._finishExperiment();
            }
        }

        _finishExperiment() {
            this.test = "DONE";
            this.phase = "FINAL";
            this.instruction = `EXPERIMENT COMPLETE | VALID TRIALS: ${this.validTrials} | EMULATED: ${this.counts.HW_EMULATED_CONTINUES} | VIEWER FALLBACK: ${this.counts.HW_VIEWER_FALLBACK_CONTINUES} | FAIL CLOSED: ${this.counts.HW_FAIL_CLOSED} | AUTO RECOVERY: ${this.counts.RECOVERY_AUTO} | YOU MAY REMOVE THE HEADSET`;
            this._event("experiment_complete", { valid_trials: this.validTrials, observed_counts: this.counts });
            this._announce("Experiment complete. You may remove the headset", [0.15, 0.15, 0.3]);
            this._render();
        }

        onFrame(observation) {
            const now = nowMs();
            this.lastObservation = observation;
            if (observation.viewerPoseSampled) this.lastViewerPoseExists = Boolean(observation.viewerPose);
            if (this.test === "T1" && this.currentTrial && this._isCriticalPhase() && !observation.move) {
                this.currentTrial.move_ever_false = true;
                this._invalidate("INVALID_MOVE_RELEASED", "MOVE RELEASED - REPEAT TRIAL", "Move released. Trial invalid");
            }
            if (this.phase === "MOVE_BUTTON_CHECK") this._handleMoveCheck(observation, now);
            else if (this.phase === "HOLD_MOVE") this._handleHoldMove(observation, now);
            else if (this.phase === "BASELINE" && this.test === "T0") this._handleT0(observation, now);
            else if (this.phase === "BASELINE" && this.test === "T1") this._handleT1Baseline(observation, now);
            else if (["OCCLUDE", "LOSS_DETECTED"].includes(this.phase) && this.test === "T1") this._handleOcclude(observation, now);
            else if (["OCCLUDE", "RESTORE"].includes(this.phase) && this.test === "T4") this._handleT4(observation, now);
            else if (this.phase === "RESTORE") this._handleRestore(observation);
            else if (this.phase === "RECOVERY") this._handleRecovery(observation, now);
            else if (this.phase === "INVALID" && this.invalidUntilMs !== null && now >= this.invalidUntilMs) {
                this.currentTrial = null;
                this.moveTrueSinceMs = null;
                this._setPhase("READY", this.test === "T1"
                    ? `T1 TRIAL ${this.validTrials + 1}/5 - PRESS LEFT TRIGGER`
                    : this.test === "T4"
                        ? "T4 OPTIONAL - SHORT PRESS TO RUN, LONG PRESS TO SKIP"
                        : "PRESS LEFT TRIGGER TO BEGIN T0");
            }
            if (now - this.lastRawSampleMs >= this.config.rawSampleIntervalMs) {
                this._event("frame_sample");
                this.lastRawSampleMs = now;
            }
            if (this.phase === "MOVE_BUTTON_CHECK" && !this.speechSupported
                && now - this.lastMoveReminderMs >= 4000) {
                this._beep([0.05, 0.05, 0.22]);
                this.lastMoveReminderMs = now;
            }
            this.lastControllerEmulated = observation.controllerPose
                ? Boolean(observation.controllerPose.emulatedPosition)
                : null;
            this._render();
        }

        getStateForTest() {
            return {
                test: this.test,
                trial: this.trial,
                validTrials: this.validTrials,
                phase: this.phase,
                instruction: this.instruction,
                sidebandConnected: this.sidebandConnected,
                domOverlayType: this.domOverlayType,
            };
        }
    }

    global.SpesQuestExperimentOperator = QuestExperimentOperator;
})(globalThis);
