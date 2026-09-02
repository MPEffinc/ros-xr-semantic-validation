# Feasibility Experiment Results

## Environment

- Test date: 2026-08-25
- ROS 2: Humble on Ubuntu 22.04 Jammy container
- RMW: Fast DDS (`rmw_fastrtps_cpp`)
- SROS2: 0.10.9, `Enforce` mode
- Bridge: `rosbridge_suite` 2.0.7, loopback WebSocket only
- Enclaves: `/robot`, `/authorized`, `/low`, `/trusted_bridge`
- Reproduction: `./ros_env/run_feasibility.sh`

## Test A: Authorized Direct Publish

- Expected: `/authorized`가 `/cmd_vel` publish, Dummy Robot 수신
- Observed: `linear.x=0.330`을 `/robot` Dummy Robot이 수신
- Result: PASS — ALLOW

## Test B: Low-Privilege Direct Publish

- Expected: `/low`의 동일 message type publish 차단, Dummy Robot 미수신
- Observed: `/low` node의 graph 참여 후 Fast DDS가 `rt/cmd_vel` writer 생성을 deny rule로 차단했으며 `linear.x=0.440`은 수신되지 않음
- Result: PASS — BLOCK

## Test C: External Client via Trusted Bridge

- Expected: 두 WebSocket Client의 명령을 `/trusted_bridge`가 `/cmd_vel`로 publish
- Observed: Client A의 `linear.x=0.440`과 Client B의 `linear.x=0.550`을 모두 Dummy Robot이 수신
- Result: PASS — ALLOW

## Identity Observation

- ROS publisher node: `/rosbridge_websocket`
- SROS2 enclave: `/trusted_bridge`
- A와 B가 동시에 연결된 동안 `/cmd_vel` publisher count는 1이고 endpoint GID도 동일
- ROS graph node set에는 `/dummy_robot`과 `/rosbridge_websocket`만 존재하며 External Client A/B는 ROS node로 표현되지 않음
- A만 종료하고 B가 남았을 때 같은 publisher/GID가 유지됨
- B도 종료하고 unregister timeout이 지난 뒤 publisher count는 0이 됐지만 rosbridge node는 유지됨

## Interpretation

확인된 사실:

- `/low`의 direct `linear.x=0.440`은 SROS2가 차단했다.
- 동일한 `linear.x=0.440`을 External Client A가 rosbridge로 보내면 `/trusted_bridge` 권한으로 전달됐다.
- 이 구성의 여러 WebSocket Client는 ROS/DDS에서 client별 principal이 아니라 하나의 bridge node와 enclave로 축약됐다.
- SROS2는 주어진 ROS/DDS principal과 policy에 따라 의도대로 동작했다.

아직 확인되지 않은 가설:

- 실제 XR client, Quest 또는 공개 XR–ROS framework에서도 같은 identity 축약이 발생하는지는 확인하지 않았다.
- Session Authority, Focus Loss, 실제 robot impact 및 기존 방어 우회는 확인하지 않았다.
- 이 결과만으로 SROS2 취약점, 완성된 XR 공격 또는 최종 novelty를 주장할 수 없다.

현재 판단:

- 최소 Feasibility: GO
- 전체 연구 Item: CONDITIONAL GO

## Blockers

- 없음

## Quest2ROS2 ROS–TCP Framework Validation

### Environment and Revision

- Test date: 2026-08-25
- ROS 2 Humble / Fast DDS / SROS2 `Enforce`
- Quest2ROS2: `main@07aaf65149c9e29103f1fc61deb466cef8a55cef`
- ros_tcp_communication: `main@5c5f08956d4bc7a045c321214b0bc03c63eb20a7`
- Built without third-party source patch: `quest2ros`, `ros_tcp_endpoint`, `q2r2_bringup`, `origin_test`
- Endpoint: container loopback `127.0.0.1:10000`; host port/host network/privileged mode 없음
- Selected framework Topic: `/q2r_right_hand_twist`, `geometry_msgs/msg/Twist`
- Reproduction: `./ros_env/run_quest2ros2_feasibility.sh`

### SROS2 Policy

- `/dummy_receiver`: `/q2r_right_hand_twist` subscribe
- `/authorized`: `/q2r_right_hand_twist` publish
- `/low`: `/q2r_right_hand_twist` publish explicit deny
- `/trusted_quest_bridge`: Endpoint main Node와 dynamic Topic publisher에 필요한 최소 resource 허용

### Direct Publish

- Authorized `linear.x=0.330`: Dummy Receiver 수신 — **ALLOW / PASS**
- Low `linear.x=0.440`: Fast DDS가 `rt/q2r_right_hand_twist` DataWriter를 deny rule과 `check_create_datawriter`에서 차단, Dummy Receiver 미수신 — **BLOCK / PASS**

### Bridge Publish

- 실제 Endpoint framing, `__handshake`, `__publish`, 48-byte Twist payload를 구현한 TCP emulator 사용
- Client A `linear.x=0.440`: Dummy Receiver 수신 — **ALLOW / PASS**
- ROS Publisher: `/q2r_right_hand_twist_RosPublisher`
- SROS2 Enclave: `/trusted_quest_bridge`
- Direct Low와 동일한 logical value가 trusted Endpoint를 경유하면 전달됨

### Multi-Client Identity

- A가 Topic을 등록한 뒤 B는 별도 TCP connection에서 server-global registration을 사용했다.
- A `0.440`과 B `0.550`을 모두 수신했다.
- A/B 동시 연결 중 publisher count는 1이고 GID는 `d14bceb8daa86d4ca4bada6300001f030000000000000000`으로 동일했다.
- External Client A/B는 ROS graph에 Node로 나타나지 않았다.
- B의 registration 생략은 registry scope를 검증하기 위한 probe이며 실제 Quest app reconnect 절차는 확인하지 않았다.

### Disconnect and Reconnect

- A 종료 후 B 연결 중 publisher/Enclave/GID 유지
- 모든 TCP Client 종료 후에도 publisher count 1과 같은 GID 유지
- Client C가 재등록 없이 reconnect해 `linear.x=0.660` 전달, 같은 GID 재사용
- Client D가 같은 Topic을 재등록하면 publisher count 1과 graph node set은 유지되지만 GID가 `d14bceb8daa86d4ca4bada6300002d030000000000000000`으로 교체됨
- D 재등록 뒤 Fast DDS topic endpoint의 node association은 `_NODE_NAME_UNKNOWN_`으로 관찰됐고, 별도 node list에는 `/q2r_right_hand_twist_RosPublisher`가 존재함
- Endpoint process 종료 후 publisher count 0

### Difference from Generic rosbridge PoC

- 공통: External Client는 ROS principal로 나타나지 않고 trusted Bridge-side Enclave 권한으로 publish
- rosbridge: 모든 Client 종료 후 unregister timeout을 거쳐 publisher 제거
- Quest ROS–TCP: publisher registry에 client ownership이 없어 모든 Client 종료 후에도 publisher 잔존
- Quest ROS–TCP: 동일 Topic 재등록 시 기존 publisher를 교체하고 GID rotation 발생
- Quest stack은 Client가 Topic/Type registration을 요청하지만 실제 payload converter는 Quest 관련 Topic 목록만 처리하며 `/cmd_vel` payload는 처리하지 않음

### Research Decision

- Quest2ROS2 ROS-side principal/trust collapse feasibility: **GO**
- Authenticated Viewer/Operator privilege laundering: **NOT ESTABLISHED** — framework에 authentication/role boundary가 없음
- Publisher lifecycle persistence: **GO**, 단 full Session Resurrection은 확인하지 않음
- 전체 연구 Item: **CONDITIONAL GO**

### Blockers and Limits

- Quest2ROS2 target tree에는 실제 Quest/Unity app source가 없어 실제 client registration·authentication·session behavior는 미확인
- Twist Topic은 framework-native input이지만 현재 main arm controller는 Pose와 Inputs를 사용하므로 robot actuation 또는 physical impact는 미확인
- Bridge-local ACL, per-client process/enclave baseline 비교 미수행
