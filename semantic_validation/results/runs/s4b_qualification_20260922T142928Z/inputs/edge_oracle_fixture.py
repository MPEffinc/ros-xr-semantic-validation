#!/usr/bin/env python3
import argparse
import asyncio
import json
import time
from pathlib import Path

import websockets


def append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("custom", "disconnect", "hang"), required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()

    async def handler(websocket):
        count = 0
        async for raw in websocket:
            count += 1
            event = json.loads(raw)
            received_ns = time.monotonic_ns()
            if args.mode == "hang":
                append_jsonl(args.log, {"mode": args.mode, "count": count, "received_monotonic_ns": received_ns, "event": event})
                await asyncio.sleep(2.0)
                continue
            if args.mode == "custom":
                verdict = bool(event.get("tracked", False))
            else:
                verdict = True
            append_jsonl(args.log, {"mode": args.mode, "count": count, "received_monotonic_ns": received_ns, "event": event, "verdict": verdict})
            await websocket.send(json.dumps({"verdict": verdict}))
            if args.mode == "disconnect":
                await websocket.close()
                return

    async with websockets.serve(handler, "127.0.0.1", args.port):
        await asyncio.Future()


asyncio.run(main())
