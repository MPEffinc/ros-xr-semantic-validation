# 기준 DB

`blueprint.json`が修改的単一기준ではなく、**수정하는 단일 기준**이다. 조사/실험 결과는 tables의 사례·matrix·문헌·한계에 ID로 연결해 갱신하고 `python3 xr_ros_blueprint_v1/scripts/refresh_views.py`로 CSV를 재생성한다. CSV는 직접 수정하지 않는다.

KNOWN_METHOD는 제한된 조건의 기존 방법 존재, IMPLEMENTATION_GAP는 구현 누락, CANDIDATE는 검증 질문, UNKNOWN은 근거 부족이다. 원리/코드/대역 실험/실제 앱/물리 실행의 evidence level을 보존한다. 확정 gap은 별도 case의 비교 근거로 입증해야 한다.

저자 한계는 attribution·locator·판본·followup_status와 함께 남긴다. 우리 해석 및 전문 미추출을 구분한다. 원문 발췌문이 아닌 요약이다. seed_inventory 94건은 계승 자료로 이번에 모두 검증하지 않았다.

2026-10-02 기존 조사 DB를 저장소로 이전했다. 신규 실험은 없다. 과거 자료의 snapshot은 보존하고 후속 수정은 Git 이력으로 추적한다. 시트에 자동으로 접근하지 않는다.
