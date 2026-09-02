#!/usr/bin/env python3

"""Read-only HTTPS/WSS readiness probe for a running Spes experiment server."""

import argparse
import asyncio
import hashlib
import json
import ssl
import urllib.request
from pathlib import Path


async def probe_wss(host: str, port: int, context: ssl.SSLContext) -> dict:
    import websockets

    async with websockets.connect(f"wss://{host}:{port}/experiment", ssl=context) as sideband:
        hello = json.loads(await asyncio.wait_for(sideband.recv(), timeout=3.0))
        await sideband.send(json.dumps({"type": "ping"}))
        pong = json.loads(await asyncio.wait_for(sideband.recv(), timeout=3.0))
    async with websockets.connect(f"wss://{host}:{port}/ws", ssl=context):
        production_handshake = True
    return {
        "experiment_wss": hello.get("type") == "experiment_hello" and pong.get("type") == "pong",
        "production_wss": production_handshake,
        "run_id": hello.get("run_id"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4443)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(
        f"https://{args.host}:{args.port}/", context=context, timeout=3.0
    ) as response:
        page = response.read()
    certificate = ssl.get_server_certificate((args.host, args.port))
    certificate_sha256 = hashlib.sha256(certificate.encode("ascii")).hexdigest()
    wss = asyncio.run(probe_wss(args.host, args.port, context))
    result = {
        "event": "spes_server_probe",
        "https": response.status == 200 and b"quest-operator.js" in page,
        "certificate_pem_sha256": certificate_sha256,
        **wss,
    }
    result["result"] = "PASS" if result["https"] and result["experiment_wss"] and result["production_wss"] else "FAIL"
    rendered = json.dumps(result, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
