# XR→ROS 연구 참고 자료와 운영 규칙

연구 배경은 xr_ros_blueprint_v1/README.md, STATUS.md, CONTEXT.md, BLUEPRINT.md와 data/blueprint.json에 있다. 이번 회차의 수행 범위·순서·완료 조건은 사용자가 별도로 전달한 프롬프트를 따른다. CONTEXT와 STATUS의 후보/backlog 및 BLUEPRINT의 중장기 계획을 현재 실행 지시로 해석하지 않는다.

- 사용자 결정(2026-10-02): 시트는 해당 회차에서 명시적으로 요청한 경우에만 접근한다. 자동 읽기/수정/동기화하지 않는다.
- 연구 상황과 context는 GitHub의 Markdown/DB에 관리한다. CSV는 JSON에서 생성한 뷰다.
- 기존 semantic_evidence_framework, archive, Deprecated, 다른 branch/worktree/컨테이너 및 frozen protocol/raw/result를 보존한다. 적용되는 AGENTS.md와 사용자 미커밋 변경도 보존한다. force push/reset/clean 금지.
- 승인된 회차 작업의 checkpoint는 commit·push로 남기고 실제 remote SHA 확인 결과를 기록한다. 완료·미실행·환경 차단을 구분한다.
- 실제 앱/대역 앱/합성 입력/시뮬레이션/물리 로봇과 원리/code/실행의 근거 수준을 구분한다.
- 기존 방법으로 해결된 사례도 저자 가정/한계/후속 해결을 남긴다. UNKNOWN이나 limitation을 확정 gap으로 쓰지 않는다.

현재 구체적인 연구 작업은 별도 사용자 프롬프트로 지정된다.

## 결과 전달과 다음 회차

연구 진행은 사용자 결정(2026-10-03)에 따라 다음 순서로 이어진다: ChatGPT의 회차별 지시 → Claude Code의 수행 및 기술 보고 → ChatGPT의 보고와 GitHub 근거 검토 → ChatGPT의 쉬운 설명 → ChatGPT의 다음 판단, 그 이유와 별도 Claude Code 프롬프트 제공.

Claude Code는 실행 조건, 근거, 결과, 한계, 미실행 항목과 commit/remote 확인을 기술 보고로 남긴다. 사용자에게 쉽게 설명하고 다음 작업을 결정하여 지시하는 역할은 ChatGPT가 맡는다. 다음 후보는 추천으로 기록하며 별도 지시 없이 자동 실행하지 않는다.

## 부재 중 승인된 연속 작업

사용자는 2026-10-03 부재 중에도 연구가 이어지도록 요청했다. 별도 사용자 프롬프트가 승인한 여러 단계와 조건부 분기는 매 단계의 추가 답변을 기다리지 않고 진행할 수 있다. 차단된 분기는 근거를 남기고 승인된 독립 작업으로 이어간다. 승인 범위 밖의 자원·권한·대상 변경은 보류하며, 이 요청을 무제한 실험이나 무기한 반복으로 해석하지 않는다. 실행 범위와 종료 조건은 그 회차의 별도 프롬프트가 정한다.
