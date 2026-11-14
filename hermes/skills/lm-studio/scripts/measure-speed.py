#!/usr/bin/env python3
"""Measure LM Studio inference speed: TTFT + generation tok/s.

Streams a test prompt through /v1/chat/completions and reports:
  - time to first token (TTFT)
  - content/reasoning chunk counts (~token counts; LM Studio emits ~1 chunk/token)
  - generation speed in tok/s over the content stream

Usage:
    python3 measure-speed.py                          # first model from /v1/models
    python3 measure-speed.py --model qwen/qwen3.8-27b@q8_0
    python3 measure-speed.py --prompt "..." --max-tokens 400
"""
import argparse
import json
import time
import urllib.request

BASE = "http://127.0.0.1:1234/v1"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default=None, help="Model id; defaults to first from /v1/models")
    p.add_argument("--prompt", default="用中文写一段约200字的关于春天的短文")
    p.add_argument("--max-tokens", type=int, default=400)
    a = p.parse_args()

    if not a.model:
        with urllib.request.urlopen(BASE + "/models", timeout=30) as r:
            data = json.load(r)["data"]
            if not data:
                raise SystemExit("no models loaded — load one in LM Studio first")
            model = data[0]["id"]
    else:
        model = a.model

    req = urllib.request.Request(
        BASE + "/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": a.prompt}],
            "max_tokens": a.max_tokens,
            "stream": True,
        }).encode(),
        headers={"Content-Type": "application/json"},
    )

    t0 = time.time()
    ttft = None
    n_content = 0
    n_reasoning = 0
    times = []
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            d = json.loads(payload)
            ch = (d.get("choices") or [{}])[0].get("delta", {})
            now = time.time()
            c = ch.get("content") or ""
            rc = ch.get("reasoning_content") or ""
            if ttft is None and (c or rc):
                ttft = now - t0
            if c:
                n_content += 1
                times.append(now)
            if rc:
                n_reasoning += 1

    total = time.time() - t0
    print(f"model: {model}")
    print(f"TTFT (first token): {ttft:.2f}s")
    print(f"content chunks (~tokens): {n_content}, reasoning chunks: {n_reasoning}")
    if len(times) > 5:
        gen = times[-1] - times[0]
        print(f"generation speed: ~{(len(times) - 1) / gen:.1f} tok/s (chunk-based estimate)")
    else:
        print("generation speed: n/a (too few content chunks)")
    print(f"total elapsed: {total:.2f}s")


if __name__ == "__main__":
    main()
