#!/usr/bin/env bash
# A04 probe (separate ledger; no Monado, no DoS). Two containers share a host scratch dir: the server container mounts it
# read-write; client containers mount it READ-ONLY (:ro) and try to connect, as root and as uid 2001.
# Cases: socket mode 0755 and 0777. Output: one JSON line per attempt.
set -e; D=$1; IMG=m3-ordering-mux:v1; H=$(cd "$(dirname "$0")" && pwd)
for MODE in ${MODES:-755 777}; do
  rm -rf $D/s; mkdir -p $D/s; chmod 777 $D/s
  sg docker -c "docker run -d --rm --name a04srv --network none -v $D/s:/s -v $H:/p:ro $IMG python3 /p/sock_server.py /s/app.sock $MODE 20" > /dev/null
  sleep 2
  for U in 0 2001; do
    r=$(sg docker -c "docker run --rm --network none --user $U -v $D/s:/s:ro -v $H:/p:ro $IMG python3 /p/sock_client.py /s/app.sock monado-ctl-admin")
    echo "{\"mode\":\"0$MODE\",\"client_mount\":\"ro\",\"client\":$r}"
  done
  sleep 1; sg docker -c "docker logs a04srv" | sed "s/^/{\"mode\":\"0$MODE\",\"server_saw\":/; s/\$/}/"
  sg docker -c "docker rm -f a04srv" > /dev/null 2>&1 || true
done
