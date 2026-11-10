#!/usr/bin/env python3
"""Connect your unit agent to the provost (Python 3.9+, standard library only).

    # practice: provost container on your own laptop
    python connect.py --unit SENG --agent ../my_team/agent.py

    # final integration: the instructor's provost on the class network
    python connect.py --unit SENG --agent ../my_team/agent.py --provost http://<instructor-ip>:8370

    # download your unit's resource envelope to develop against
    python connect.py envelope --unit SENG --out envelope.json

Your agent never opens a port: this script dials OUT to the provost, waits
for requests, calls your agent.run_agent(request), and sends back the dict it
returns. Exceptions in your agent are reported as status "failed" instead of
crashing the connection.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_PROVOST = os.environ.get("PROVOST_URL", "http://localhost:8370")


def http(method: str, url: str, body=None, timeout=40):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"error": raw.decode(errors="replace")}


def load_agent(path: str):
    p = Path(path).resolve()
    if not p.exists():
        sys.exit(f"agent file not found: {p}")
    sys.path.insert(0, str(p.parent))  # so your agent can import its own modules
    spec = importlib.util.spec_from_file_location("unit_agent", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not callable(getattr(mod, "run_agent", None)):
        sys.exit(f"{p} does not define run_agent(request: dict) -> dict")
    return mod.run_agent


def failed(req, msg):
    return {"protocol_version": "1.0", "request_id": req.get("request_id"), "unit": req.get("unit"),
            "status": "failed", "result": {}, "warnings": [], "errors": [msg]}


def register(base, unit, team):
    while True:
        try:
            code, body = http("POST", f"{base}/api/register", {"unit": unit, "team": team})
            if code == 200:
                print(f"connected to {base} as {body['unit']} ({body['mode']} mode)", flush=True)
                return body["token"]
            sys.exit(f"registration refused ({code}): {body}")
        except (urllib.error.URLError, OSError) as e:
            print(f"provost not reachable at {base} ({e}); retrying in 3s...", flush=True)
            time.sleep(3)


def serve(args):
    run_agent = load_agent(args.agent)
    base = args.provost.rstrip("/")
    token = register(base, args.unit, args.team)
    while True:
        try:
            code, body = http("GET", f"{base}/api/poll?token={token}", timeout=40)
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            print(f"connection problem ({e}); retrying...", flush=True)
            time.sleep(2)
            continue
        if code == 401:
            token = register(base, args.unit, args.team)
            continue
        if code != 200 or not body:
            continue
        req = body["request"]
        op = req.get("operation")
        print(f"<- {req['request_id']} {op}", flush=True)
        t0 = time.time()
        try:
            resp = run_agent(json.loads(json.dumps(req)))  # hand the agent a private copy
            json.dumps(resp)
        except Exception as e:  # noqa: BLE001 - report, don't crash
            traceback.print_exc()
            resp = failed(req, f"agent raised {type(e).__name__}: {e}")
        status = resp.get("status") if isinstance(resp, dict) else "?"
        print(f"-> {req['request_id']} {op} status={status} ({time.time() - t0:.1f}s)", flush=True)
        if args.save_dir:
            d = Path(args.save_dir)
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{req['request_id']}.json").write_text(json.dumps({"request": req, "response": resp}, indent=2))
        for _ in range(5):
            try:
                code, body = http("POST", f"{base}/api/respond",
                                  {"token": token, "request_id": req["request_id"], "response": resp})
                if code != 200:
                    print(f"   provost did not accept the response ({code}): {body}", flush=True)
                break
            except (urllib.error.URLError, OSError) as e:
                print(f"   send failed ({e}); retrying", flush=True)
                time.sleep(1)


def envelope(args):
    code, body = http("GET", f"{args.provost.rstrip('/')}/api/envelope?unit={urllib.request.quote(args.unit)}")
    if code != 200:
        sys.exit(f"error {code}: {body}")
    text = json.dumps(body, indent=2)
    if args.out:
        Path(args.out).write_text(text)
        print(f"wrote {args.out}: {len(body['courses'])} courses, {len(body['rooms'])} rooms, {len(body['timeslots'])} timeslots")
    else:
        print(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="serve", choices=["serve", "envelope"])
    ap.add_argument("--provost", default=DEFAULT_PROVOST, help=f"provost URL (default {DEFAULT_PROVOST}, or $PROVOST_URL)")
    ap.add_argument("--unit", required=True, help="unit code (e.g. SENG) or full name")
    ap.add_argument("--agent", default="agent.py", help="path to your agent.py (default ./agent.py)")
    ap.add_argument("--team", default=os.environ.get("TEAM_NAME", ""), help="team name shown on the dashboard")
    ap.add_argument("--save-dir", help="save every request/response pair here (handy for building tests)")
    ap.add_argument("--out", help="envelope: write to this file")
    args = ap.parse_args()
    (envelope if args.command == "envelope" else serve)(args)


if __name__ == "__main__":
    main()
