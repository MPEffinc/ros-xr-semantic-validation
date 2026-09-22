#!/usr/bin/env bash
set -euo pipefail

ADB="${ADB:-/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb}"
PORT="${QUEST_ADB_PORT:-5555}"

echo "[1/5] ADB 확인"
if [[ ! -x "$ADB" ]]; then
    echo "ERROR: adb 없음: $ADB"
    return 1 2>/dev/null || exit 1
fi

echo "ADB: $ADB"

echo
echo "[2/5] 기존 무선 Quest 연결 확인"

WIRELESS="$(
    "$ADB" devices -l |
    awk '$2 == "device" && $1 ~ /:[0-9]+$/ && $0 ~ /model:Quest_/ {print $1; exit}'
)"

if [[ -n "$WIRELESS" ]]; then
    echo "이미 무선 연결된 Quest 발견: $WIRELESS"

    if "$ADB" -s "$WIRELESS" get-state >/dev/null 2>&1; then
        QUEST_ADB="$WIRELESS"
        export QUEST_ADB

        echo
        echo "[3/5] Quest 확인"
        MODEL="$("$ADB" -s "$QUEST_ADB" shell getprop ro.product.model | tr -d '\r')"
        echo "Model: $MODEL"

        echo
        echo "[4/5] Wi-Fi IP 확인"
        QUEST_IP="$(
            "$ADB" -s "$QUEST_ADB" shell ip route |
            tr -d '\r' |
            awk '/dev wlan0/ {
                for (i=1; i<=NF; i++)
                    if ($i=="src") { print $(i+1); exit }
            }'
        )"
        echo "Quest IP: ${QUEST_IP:-unknown}"

        echo
        echo "[5/5] READY"
        echo "QUEST_ADB=$QUEST_ADB"
        echo
        echo "이미 무선 ADB가 정상 연결되어 있으므로 USB 작업은 생략함."
        return 0 2>/dev/null || exit 0
    fi
fi

echo "기존 무선 연결 없음."

echo
echo "[3/5] USB authorized Quest 검색"

USB_SERIAL="$(
    "$ADB" devices -l |
    awk '$2 == "device" && $1 !~ /:/ && $0 ~ /usb:/ && $0 ~ /model:Quest_/ {print $1; exit}'
)"

if [[ -z "$USB_SERIAL" ]]; then
    echo "ERROR: 무선 연결도 없고 USB authorized Quest도 없음."
    echo
    "$ADB" devices -l
    return 1 2>/dev/null || exit 1
fi

echo "USB Quest: $USB_SERIAL"

QUEST_IP="$(
    "$ADB" -s "$USB_SERIAL" shell ip route |
    tr -d '\r' |
    awk '/dev wlan0/ {
        for (i=1; i<=NF; i++)
            if ($i=="src") { print $(i+1); exit }
    }'
)"

if [[ -z "$QUEST_IP" ]]; then
    echo "ERROR: Quest Wi-Fi IP 확인 실패."
    return 1 2>/dev/null || exit 1
fi

echo "Quest IP: $QUEST_IP"

echo
echo "[4/5] ADB TCP ${PORT} 활성화"
"$ADB" -s "$USB_SERIAL" tcpip "$PORT"

sleep 2

TARGET="${QUEST_IP}:${PORT}"

echo "무선 연결 시도: $TARGET"
"$ADB" connect "$TARGET"

sleep 1

if [[ "$("$ADB" -s "$TARGET" get-state 2>/dev/null || true)" != "device" ]]; then
    echo "ERROR: 무선 ADB 연결 실패."
    return 1 2>/dev/null || exit 1
fi

QUEST_ADB="$TARGET"
export QUEST_ADB

echo
echo "[5/5] READY"
echo "QUEST_ADB=$QUEST_ADB"
echo "이제 USB 케이블을 제거해도 됨."