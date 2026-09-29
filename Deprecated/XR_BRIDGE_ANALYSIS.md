# Quest2ROS2 Bridge Analysis

## 1. Scope

이 분석은 Quest2ROS2가 문서에서 지정한 ROS 2 측 stack만 대상으로 한다.

```text
Quest2ROS2
+ ros_tcp_communication
+ quest2ros message package
+ Quest/Unity 대신 실제 wire format을 따르는 TCP emulator
```

실제 Quest 2/3, Unity Editor, APK, Robot, WiVRn, Monado, OpenXR는 사용하지 않았다. Quest2ROS2 target tree에는 Unity/C# source가 없으므로 실제 Quest app의 registration·reconnect 구현은 확인하지 않았다. Runtime은 실제 `ros_tcp_endpoint` 코드를 수정하지 않고 loopback TCP에서 수행했다.

## 2. Repository Revisions

| Repository | Branch | Commit | Clone time | License | 사용 Package |
| --- | --- | --- | --- | --- | --- |
| `https://github.com/Taokt/Quest2ROS2.git` | `main` | `07aaf65149c9e29103f1fc61deb466cef8a55cef` | 2026-08-25T16:55:02+09:00 | Apache-2.0 | `q2r2_bringup`, `Files_for_msg_pkg` → `quest2ros` |
| `https://github.com/guguroro/ros_tcp_communication.git` | `main` | `5c5f08956d4bc7a045c321214b0bc03c63eb20a7` | 2026-08-25T16:55:02+09:00 | Apache-2.0 | `ros_tcp_endpoint` |

두 저장소는 detached fixed commit으로 clone했으며 source patch 없이 build했다. Quest2ROS2의 `Files_for_msg_pkg`를 `quest2ros` package로 복사한 것은 공식 설치 절차를 그대로 따른 workspace 구성이다.

주의할 upstream metadata 불일치:

- Quest2ROS2의 현재 Python code 대부분은 `quest2ros`를 import하지만 manifest는 `quest2ros2_msg`를 의존한다. `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:package.xml:19-23`, `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:q2r2_bringup/SimulationInput.py:27-33`
- Legacy `ros2quest.py`는 여전히 `quest2ros2_msg`를 import한다. `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:q2r2_bringup/ros2quest.py:1-8`
- Repository 이름은 `ros_tcp_communication`이지만 실제 ROS package 이름은 `ros_tcp_endpoint`다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:package.xml:3-10`
- Endpoint의 `package.xml` version은 0.7.0, `setup.py` version은 0.0.1이다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:package.xml:4-10`, `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:setup.py:8-22`

## 3. Framework Architecture

Quest2ROS2 target tree에는 Unity `Assets/`, `.cs`, socket implementation 또는 submodule이 없다. README는 외부 Quest2ROS app과 별도 maintained `ros_tcp_communication`을 사용하도록 지시한다. `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:README.md:20-40`, `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:README.md:96-104`

확인된 ROS-side 구조는 다음과 같다.

```text
External Quest/Unity app source — NOT VERIFIED
  ↓ ROS–TCP binary frames
ros_tcp_endpoint /UnityEndpoint
  ↓ server-global publishers_table
/q2r_<side>_hand_<kind>_RosPublisher
  ↓ Quest ROS topics
q2r2_bringup arm controller
  ↓
Cartesian target PoseStamped / GripperCommand action
```

`TcpServer`는 하나의 rclpy Node이며 기본 `0.0.0.0:10000`에 bind한다. Publisher, Subscriber, Service registry와 pending service 상태는 모두 server 객체의 전역 필드다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/server.py:35-77`

Listen thread는 connection마다 `ClientThread`를 만들지만 같은 `TcpServer` 객체를 전달한다. 따라서 socket/thread는 connection별이고 ROS registry는 공유된다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/server.py:79-106`, `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/client.py:27-46`

이번 실험은 기본 bind를 사용하지 않고 `127.0.0.1:10000`으로 override했다. Compose에는 port publication, host network, privileged mode가 없다.

## 4. Client and Session Model

Connection별로 보존되는 값은 socket, source IP/port, thread와 halt event다. Client identity, user, role, session, publisher ownership map은 없다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/client.py:27-46`, `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/client.py:190-231`

Server→Client 송신도 완전한 multi-session 구조가 아니다. `UnityTcpSender`에는 server-wide `queue` reference 하나만 있고 새 connection이 이를 자신의 local queue로 교체한다. 최신 connection 종료 시 이전 queue로 복원되지 않는다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/tcp_sender.py:42-56`, `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/tcp_sender.py:158-200`

즉 여러 inbound TCP connection은 수용되지만, 독립적인 authorization session model은 아니다.

## 5. Authentication and Authorization

두 target repository의 non-binary source에서 다음 계열을 검색했다.

```text
authentication, authorization, token, JWT, MAC, certificate,
role, user, client ID, identity, allowlist, denylist, ACL,
session, permission
```

Client 인증, Client별 role/ACL 또는 Client→ROS principal mapping 구현은 발견되지 않았다.

긍정적 코드 근거:

- Connection 직후 credential 검증 없이 sender를 시작하고 frame을 처리한다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/client.py:175-225`
- Handshake는 고정 version `v0.7.0`과 protocol `ROS2`만 포함한다. credential, challenge, client/session ID는 없다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/tcp_sender.py:168-178`, `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/tcp_sender.py:230-238`
- Source IP/port는 log 외 authorization이나 registry key로 사용되지 않는다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/client.py:33-46`, `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/client.py:190-231`

Quest2ROS2 controller의 `allow_pose_update`도 권한이 아니라 Node-local Boolean gate다. 기본값은 true이고 lower-button rising edge가 이를 toggle한다. Upper button의 gripper action은 이 pose gate와 별개다. `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:q2r2_bringup/robot_arm_controller_base.py:81-90`, `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:q2r2_bringup/robot_arm_controller_base.py:310-384`

따라서 이 framework에는 검증 가능한 Viewer/Operator privilege boundary가 없다.

## 6. Publisher and Enclave Mapping

`publishers_table`은 `TcpServer` 전체에 하나이며 Topic string을 key로 사용한다. 모든 ClientThread는 같은 table에서 publisher를 조회한다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/server.py:66-77`, `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/client.py:211-225`

Client가 Topic을 등록하면 main `/UnityEndpoint`가 직접 publish하는 것이 아니라 별도 `RosPublisher` rclpy Node가 생성된다. `q2r_right_hand_twist`의 실제 Node 이름은 `/q2r_right_hand_twist_RosPublisher`다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/publisher.py:24-43`

동일 Topic을 다시 등록하면 기존 publisher/Node를 재사용하지 않고 destroy한 뒤 새 publisher/Node로 교체한다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/server.py:224-250`, `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/publisher.py:71-78`

Runtime mapping:

| 상태 | Publisher count | ROS Node | SROS2 Enclave | GID |
| --- | ---: | --- | --- | --- |
| A 등록 | 1 | `/q2r_right_hand_twist_RosPublisher` | `/trusted_quest_bridge` | `d14bceb8daa86d4ca4bada6300001f030000000000000000` |
| A+B, B는 기존 global registration 사용 | 1 | 동일 | 동일 | 동일 |
| 모든 Client 종료 | 1 | 동일 | 동일 | 동일 |
| C 무등록 reconnect | 1 | 동일 | 동일 | 동일 |
| D 동일 Topic 재등록 | 1 | graph node set에는 동일 Node/Enclave | 동일 | `d14bceb8daa86d4ca4bada6300002d030000000000000000` |

D 재등록 뒤 Fast DDS의 endpoint→node association은 `_NODE_NAME_UNKNOWN_`이 됐다. 그러나 node list와 enclave-aware graph node set에는 `/q2r_right_hand_twist_RosPublisher@/trusted_quest_bridge`가 남았다. 이를 동일 GID라고 과장하지 않으며, “같은 이름/Enclave의 publisher replacement와 GID rotation”으로 기록한다.

## 7. Topic/Service/Action Selection

Wire frame은 다음 little-endian 구조다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/client.py:48-108`

```text
uint32 destination_length
byte[destination_length] destination
uint32 body_length
byte[body_length] body
```

Publisher registration은 destination `__publish`와 JSON body를 사용한다. JSON key는 `SysCommands.publish()` 인자로 직접 전달된다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/server.py:120-129`, `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/server.py:224-250`

```json
{
  "topic": "q2r_right_hand_twist",
  "message_name": "geometry_msgs/Twist",
  "queue_size": 10,
  "latch": false
}
```

Client는 non-empty Topic과 import 가능한 message type을 요청할 수 있고 Client별 ACL은 없다. 그러나 이 fork는 generic ROS CDR deserialization을 비활성화하고 Topic-name 기반 converter를 사용한다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/publisher.py:45-69`

실제 payload converter가 지원하는 것은 Quest 관련 Twist, Pose, Inputs, Haptic Topic 목록이다. `/cmd_vel` registration은 가능해도 payload는 `Unknown topic`으로 publish되지 않는다. 따라서 arbitrary registration과 arbitrary command delivery를 구분해야 한다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/ros_msg_converter.py:9-71`

실험은 실제 framework contract에 포함되고 converter가 지원하는 상대 wire destination `q2r_right_hand_twist`를 사용했다. ROS graph name은 `/q2r_right_hand_twist`, payload는 `<6d` 48 bytes다.

Quest2ROS2 main arm controller는 Twist가 아니라 Pose와 Inputs를 사용한다. Pose를 Cartesian target으로 변환하고 gripper Action을 보낸다. `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:q2r2_bringup/robot_arm_controller_base.py:92-133`, `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:q2r2_bringup/robot_arm_controller_base.py:211-332`

최종 hard-coded interface:

- Left: `/bh_robot/left_arm_clik_controller/target_frame`, `/bh_robot/left_arm_gripper_action_controller/gripper_cmd`. `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:q2r2_bringup/left_arm_controller.py:4-15`
- Right: `/bh_robot/right_arm_clik_controller/target_frame`, `/bh_robot/right_arm_gripper_action_controller/gripper_cmd`. `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:q2r2_bringup/right_arm_controller.py:4-15`

따라서 이번 Twist identity test는 framework-native input path이지만 실제 arm actuation test는 아니다.

## 8. Disconnect and Reconnect Behavior

Client disconnect `finally`는 halt event, socket close, log만 수행한다. Publisher ownership이나 unregister는 없다. `ros_tcp_communication@5c5f08956d4bc7a045c321214b0bc03c63eb20a7:ros_tcp_endpoint/client.py:226-231`

Runtime에서 확인된 동작:

1. A가 Topic을 등록하고 publish했다.
2. B는 별도 TCP connection으로 접속하고 `__publish`를 생략한 채 같은 destination에 publish했다.
3. A/B의 값이 모두 동일 publisher/GID에서 수신됐다.
4. A 종료 후 B가 남아 있을 때 publisher/GID가 유지됐다.
5. B까지 종료해도 publisher/GID가 유지됐다.
6. C는 reconnect 뒤 재등록 없이 기존 publisher/GID로 publish했다.
7. D가 같은 Topic을 재등록하자 publisher count는 1로 유지되면서 GID가 교체됐다.
8. Endpoint process를 종료한 뒤 publisher count가 0이 됐다.

B의 registration 생략은 server-global registry scope를 검증하기 위한 의도적 probe다. 실제 Quest app이 새 connection마다 재등록하는지는 app source 부재로 확인하지 않았다. 이 결과는 full Session Resurrection이 아니라 Bridge publisher registration lifecycle 잔존성이다.

## 9. Runtime Experiment Setup

- ROS 2 Humble / Ubuntu 22.04 container
- RMW: `rmw_fastrtps_cpp`
- SROS2: Enforce
- Endpoint: `127.0.0.1:10000`, container loopback only
- Topic: `/q2r_right_hand_twist`
- Message: `geometry_msgs/msg/Twist`
- Enclaves: `/dummy_receiver`, `/authorized`, `/low`, `/trusted_quest_bridge`
- External emulator: stdlib TCP/socket implementation, ROS Node 아님
- Source patch: 없음

Build package:

```text
quest2ros
ros_tcp_endpoint
q2r2_bringup
origin_test
```

`SimulationInput` velocity mode도 build overlay에서 실행해 Topic 수신을 확인했다. 이는 ROS-only smoke test이며 TCP identity 증거로 사용하지 않는다. `SimulationInput`은 직접 rclpy Publisher를 만든다. `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:q2r2_bringup/SimulationInput.py:35-64`, `Quest2ROS2@07aaf65149c9e29103f1fc61deb466cef8a55cef:q2r2_bringup/SimulationInput.py:67-101`

## 10. Experiment Results

| Test | Expected | Observed | Result | Evidence |
| --- | --- | --- | --- | --- |
| ROS-side package build | 고정 source build | 4 package build/import | PASS | `evidence/quest2ros2_build.log` |
| SimulationInput smoke | Quest2ROS2가 선언한 Twist Topic publish | `/q2r_right_hand_twist` 수신 | PASS | Build log; ROS-only |
| Authorized direct | ALLOW | `0.330` 수신 | PASS | Runtime log |
| Low direct | SROS2 BLOCK | `rt/q2r_right_hand_twist` deny, `check_create_datawriter`, `0.440` 미수신 | PASS | Runtime log |
| TCP Client A | Trusted Bridge ALLOW | 동일 `0.440` 수신 | PASS | Runtime/Identity log |
| Multi-client A/B | shared ROS authority 관찰 | A `0.440`, B `0.550`; publisher 1, GID 동일 | PASS | Identity `[A_B_SHARED]` |
| A disconnect | B 연결 중 publisher 유지 | Node/Enclave/GID 유지 | PASS | Runtime log |
| 모든 Client disconnect | lifecycle 관찰 | publisher count 1로 잔존 | PASS | Identity `[ALL_CLIENTS_CLOSED_PUBLISHER_PERSISTS]` |
| C reconnect no-register | global registration 재사용 | `0.660` 수신, 기존 GID | PASS | Identity `[C_RECONNECT_WITHOUT_REGISTER]` |
| D same-topic re-register | replacement 동작 확인 | count 1, GID rotation, endpoint association unknown | PASS/OBSERVED | Identity `[D_REREGISTER_GID_ROTATION]` |
| Endpoint exit | dynamic publisher 정리 | publisher count 0 | PASS | Runtime log |

## 11. Comparison with rosbridge_suite

| 항목 | rosbridge_suite PoC | Quest2ROS2 ROS–TCP |
| --- | --- | --- |
| Protocol | WebSocket/JSON | Length-prefixed TCP + JSON system command + binary payload |
| Client 인증 | 없음 | 없음 |
| Client별 Role | 없음 | 없음 |
| Topic 선택 | 실험에서 `/cmd_vel` glob으로 제한 | Client가 registration Topic/Type 요청; 실제 payload converter는 Quest Topic allowlist |
| ROS Publisher Node | `/rosbridge_websocket` | `/q2r_right_hand_twist_RosPublisher` |
| Multi-Client Publisher | A/B publisher 1개, GID 공유 | A 등록 후 B global registry 사용 시 publisher 1개, GID 공유 |
| 동일 Topic 재등록 | advertise reference 관리 | 기존 Node/Publisher 교체, GID rotation |
| SROS2 Identity | `/trusted_bridge` | `/trusted_quest_bridge` |
| 모든 Client 종료 | unregister timeout 후 publisher 0 | publisher/GID 잔존, Endpoint 종료 시 0 |
| Direct BLOCK / Bridge ALLOW | 확인 | Quest2ROS2가 선언한 Topic의 ROS-side 경로에서 확인 |
| 실제 XR Framework 연관성 | Generic | Quest2ROS2가 지정한 ROS-side stack; Quest app source는 미확인 |

공통점은 External Client가 ROS Node/Enclave principal로 나타나지 않고 Bridge-side ROS identity로 publish한다는 점이다. 가장 큰 차이는 Quest2ROS2 stack의 server-global persistent registry와 동일 Topic 재등록 시 GID replacement다.

## 12. Confirmed Facts

- Fixed commit의 ROS-side package 4개가 Humble container에서 build/import됐다.
- SROS2 `/low` direct `0.440`은 차단되고 같은 값이 TCP Endpoint를 통하면 수신됐다.
- TCP A/B는 ROS graph에 Node로 나타나지 않았다.
- A가 만든 global publisher를 B가 별도 connection에서 사용할 수 있었다.
- A/B의 값은 publisher 1개, 같은 GID, `/trusted_quest_bridge` 권한으로 전달됐다.
- 모든 Client 종료 후에도 publisher/GID가 남았고 C가 재등록 없이 재사용했다.
- 동일 Topic 재등록은 publisher replacement와 GID rotation을 만들었다.
- Endpoint code와 Quest2ROS2 controller에는 인증된 user/role boundary가 없다.
- SROS2는 주어진 ROS/DDS principal에 대해 의도대로 정책을 집행했다.

## 13. Unconfirmed Hypotheses

- 실제 Quest app이 connection마다 어떤 registration sequence를 사용하는지 확인하지 않았다.
- 실제 Quest app의 별도 인증, device identity 또는 session metadata 존재 여부를 확인하지 않았다.
- Emulator가 Endpoint parser와 framing을 따르는 것은 확인했지만 실제 Quest wire capture와 byte-for-byte 비교하지 않았다.
- Pose/Inputs를 통한 arm target 또는 gripper Action 실행은 확인하지 않았다.
- Actual Viewer/Operator privilege boundary와 그 우회는 확인하지 않았다.
- Physical impact, Focus Loss, Session Resurrection, reconnect 후 queued Action은 확인하지 않았다.
- 기존 Bridge-local ACL, per-client process/enclave가 문제를 충분히 해결하는지 비교하지 않았다.

## 14. Research Interpretation

실제 Quest2ROS2 ROS-side stack에서도 External TCP source가 SROS2 principal로 보존되지 않고 Endpoint가 생성한 ROS Node/Enclave 권한으로 전달되는 것은 확인됐다.

그러나 해당 framework에는 인증된 Viewer/Operator role이 없다. 따라서 현재 가장 정확한 표현은 다음이다.

> Unauthenticated External TCP input이 server-global registry를 통해 trusted ROS Endpoint identity로 축약되는 trust/principal collapse.

이를 “인증된 저권한 XR 사용자의 privilege laundering”이라고 부를 근거는 아직 없다. SROS2 취약점도 아니다. SROS2는 direct low writer를 정확히 차단했다.

Publisher lifecycle 잔존은 중요한 추가 관찰이지만 full Session Resurrection이 아니다. 등록 state에 client ownership이 없어서 Endpoint process lifetime까지 남는 현상이다.

## 15. GO / NO-GO Decision

- Generic Bridge minimum feasibility: **GO**
- Quest2ROS2 ROS-side principal/trust collapse feasibility: **GO**
- Quest2ROS2 authenticated-role privilege laundering: **NOT ESTABLISHED**
- Quest2ROS2 publisher lifecycle persistence: **GO**, 단 Session Resurrection claim은 금지
- 전체 Research Item: **CONDITIONAL GO**

진행 조건:

1. 실제 Quest app source 또는 wire capture로 authentication/session/registration model 확인
2. 실제로 구분되는 upstream privilege boundary 확보
3. Bridge-local ACL/per-client process/per-client enclave baseline과 비교
4. Pose/Inputs→safe controller target까지 영향 경로 확인

실제 app에도 role/auth boundary가 없다면 이 framework에서 “Privilege Laundering” 방향은 중단하고 unauthenticated bridge exposure와 구분하거나, 명시적 multi-role XR–ROS framework로 대상을 전환해야 한다.

## 16. Next Recommended Step

다음 작업 하나는 **Quest2ROS2가 요구하는 실제 Quest2ROS app의 정확한 source/revision 또는 loopback-safe wire capture를 확보해 connection registration과 identity/auth metadata를 검증하는 것**이다.

시작 조건:

- 공개 source가 있으면 commit을 고정해 정적 분석
- source가 없으면 실제 장비를 사용하기 전에 capture 항목과 안전한 Topic을 사전 정의
- credential/user/role이 없다면 privilege-laundering claim을 중단하고 다른 실제 framework 후보로 전환

이 단계 전에는 ORBIT, eBPF/LSM 또는 physical robot 실험으로 확장하지 않는다.
