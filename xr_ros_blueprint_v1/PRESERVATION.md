# 보존 경계

이번 추가는 원격 research/xr-ros-evidence-framework의 eff464c를 출발점으로 CLAUDE.md와 새 xr_ros_blueprint_v1/ 파일만 추가한다. semantic_evidence_framework/, archive/, Deprecated/, 기존 README와 다른 branch의 내용은 변경하지 않는다.

원격 API 작업에서는 host local의 미커밋 변경·컨테이너 상태를 확인할 수 없다. Claude는 local 작업 전에 이를 따로 확인하고 safe fast-forward 또는 분리된 worktree를 사용해야 한다. 이전 컨테이너 3개와 다른 checkout을 건드리지 않는다.

원문 자료와 이전 실험은 pinned commit/locator로 연결돼 있다. 기존 protocol/raw/result의 사후 수정은 금지하고 정정은 별도 파일로 남긴다. 이번 조사 snapshot의 범위를 실험 결과로 확장하지 않는다.
