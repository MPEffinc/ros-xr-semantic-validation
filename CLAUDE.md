# XR→ROS 연구 참고 자료와 운영 규칙

연구 배경은 xr_ros_blueprint_v1/README.md, STATUS.md, CONTEXT.md, BLUEPRINT.md와 data/blueprint.json에 있다. 이번 회차의 수행 범위·순서·완료 조건은 사용자가 별도로 전달한 프롬프트를 따른다. CONTEXT와 STATUS의 후보/backlog 및 BLUEPRINT의 중장기 계획을 현재 실행 지시로 해석하지 않는다.

- 사용자 결정(2026-10-02): 시트는 해당 회차에서 명시적으로 요청한 경우에만 접근한다. 자동 읽기/수정/동기화하지 않는다.
- 연구 상황과 context는 GitHub의 Markdown/DB에 관리한다. CSV는 JSON에서 생성한 뷰다.
- 기존 semantic_evidence_framework, archive, Deprecated, 다른 branch/worktree/컨테이너 및 frozen protocol/raw/result를 보존한다. 적용되는 AGENTS.md와 사용자 미커밋 변경도 보존한다. force push/reset/clean 금지.
- 승인된 회차 작업의 checkpoint는 commit·push로 남기고 실제 remote SHA 확인 결과를 기록한다. 완료·미실행·환경 차단을 구분한다.
- 실제 앱/대역 앱/합성 입력/시뮬레이션/물리 로봇과 원리/code/실행의 근거 수준을 구분한다.
- 기존 방법으로 해결된 사례도 저자 가정/한계/후속 해결을 남긴다. UNKNOWN이나 limitation을 확정 gap으로 쓰지 않는다.

현재 구체적인 연구 작업은 별도 사용자 프롬프트로 지정된다.
