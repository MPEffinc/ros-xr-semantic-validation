# XR→ROS 연구 운영 규칙

현재 연구 진입점은 `xr_ros_blueprint_v1/README.md`, `STATUS.md`, `CONTEXT.md`다. 그 순서로 읽고 CONTEXT의 실행 지시를 따른다. 과거 독립 gate 확대 보류는 모든 XR→ROS 사례의 종료가 아니다.

- 사용자 결정(2026-10-02): 시트는 사용자가 해당 작업에서 명시적으로 요청할 때만 접근한다. 자동 읽기/수정/동기화하지 않는다.
- 실제 진행 상태와 context는 GitHub 저장소의 Markdown과 `xr_ros_blueprint_v1/data/blueprint.json`에 갱신한다. CSV는 생성 뷰다.
- 기존 semantic_evidence_framework, archive, Deprecated, 다른 branch/worktree/컨테이너, frozen protocol/raw/result는 보존한다.
- 작업 전에 적용되는 AGENTS.md와 local 미커밋 변경을 확인한다. routine 연구 작업은 자율 진행하고 checkpoint마다 commit·push 및 remote SHA 일치를 확인한다. force push/reset/clean 금지.
- 실제 앱/대역 앱/합성 입력/시뮬레이션/물리 로봇을 구분한다. 코드 원리와 실제 실행을 같은 근거로 표시하지 않는다.
- 기존 방법으로 해결된 사례도 저자 가정/한계, 후속 해결, 실제 배치 제한을 남긴다. UNKNOWN과 limitation을 확정 gap으로 쓰지 않는다.
- 프레임워크는 반복되는 통합 문제와 강한 비교군 대비 이득이 확인될 때 제작·평가한다.
