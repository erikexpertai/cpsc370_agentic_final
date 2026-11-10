#!/usr/bin/env python3
"""Interface-compliance checker: the same schema checks the provost runs on
every response (Protocol 1.0). Standard library only.

    python check_response.py request.json response.json
    python check_response.py input_samples/01_generate_schedule.request.json my_response.json

or from Python:

    from check_response import check_response
    issues = check_response(request, response)   # [] == compliant

This checks the *interface* only. Hard constraints (capacity, overlaps,
features, availability...) are your agent's job; the provost reports any it
finds on the dashboard and in outputs/<run>/messages.jsonl
("type": "hard_constraint_check").
"""

from __future__ import annotations

import json
import sys

PROTOCOL_VERSION = "1.0"
STATUSES = ("completed", "partial", "failed")


def check_response(request: dict, resp) -> list[str]:
    """Schema problems with a unit response. Empty list == compliant."""
    issues = []
    if not isinstance(resp, dict):
        return ["response is not a JSON object"]
    try:
        json.dumps(resp)
    except (TypeError, ValueError) as ex:
        issues.append(f"response not JSON-serializable: {ex}")
    for k, typ in (("protocol_version", str), ("request_id", str), ("unit", str), ("status", str),
                   ("result", dict), ("warnings", list), ("errors", list)):
        if k not in resp:
            issues.append(f"missing field {k!r}")
        elif not isinstance(resp[k], typ):
            issues.append(f"field {k!r} should be {typ.__name__}")
    if resp.get("protocol_version") != PROTOCOL_VERSION:
        issues.append("protocol_version must be '1.0'")
    if resp.get("request_id") != request.get("request_id"):
        issues.append("request_id not echoed unchanged")
    if resp.get("unit") != request.get("unit"):
        issues.append("unit does not match request")
    if resp.get("status") not in STATUSES:
        issues.append(f"status must be one of {STATUSES}")
    result = resp.get("result") if isinstance(resp.get("result"), dict) else {}
    if resp.get("status") == "failed":
        if not resp.get("errors"):
            issues.append("status 'failed' but errors is empty")
        return issues

    op = request.get("operation")
    if op in ("generate_schedule", "repair_schedule"):
        sched = result.get("schedule")
        if not isinstance(sched, list):
            issues.append("result.schedule must be a list")
        else:
            for i, e in enumerate(sched):
                if not isinstance(e, dict):
                    issues.append(f"schedule[{i}] not an object")
                    continue
                for k in ("course_id", "timeslot_id", "room_id"):
                    if not isinstance(e.get(k), str):
                        issues.append(f"schedule[{i}].{k} missing or not a string")
                if op == "generate_schedule":
                    if not isinstance(e.get("rationale"), list):
                        issues.append(f"schedule[{i}].rationale must be a list")
                    ps = e.get("preference_score")
                    if not isinstance(ps, (int, float)) or isinstance(ps, bool) or not 0 <= ps <= 1:
                        issues.append(f"schedule[{i}].preference_score must be a number in [0,1]")
        if not isinstance(result.get("unresolved"), list):
            issues.append("result.unresolved must be a list")
        if not isinstance(result.get("summary"), str):
            issues.append("result.summary must be a string")
        if resp.get("status") == "partial" and not result.get("unresolved"):
            issues.append("status 'partial' but unresolved is empty")
    if op == "repair_schedule":
        ch = result.get("changes")
        if not isinstance(ch, list):
            issues.append("result.changes must be a list")
        else:
            for i, c in enumerate(ch):
                for k in ("course_id", "old_timeslot_id", "old_room_id", "new_timeslot_id", "new_room_id", "reason"):
                    if not isinstance(c, dict) or k not in c:
                        issues.append(f"changes[{i}] missing {k!r}")
                        break
            if result.get("change_count") != len(ch):
                issues.append("change_count must equal len(changes)")
    if op == "evaluate_change":
        if result.get("decision") not in ("accept", "reject"):
            issues.append("result.decision must be 'accept' or 'reject'")
        if not isinstance(result.get("reason"), str) or not result.get("reason"):
            issues.append("result.reason must be a non-empty string")
        s = result.get("impact_score")
        if not isinstance(s, (int, float)) or isinstance(s, bool) or not 0 <= s <= 1:
            issues.append("result.impact_score must be a number in [0,1]")
        alts = result.get("alternatives", [])
        if not isinstance(alts, list):
            issues.append("result.alternatives must be a list")
        else:
            for i, a in enumerate(alts):
                if not isinstance(a, dict) or not isinstance(a.get("timeslot_id"), str) or not isinstance(a.get("room_id"), str):
                    issues.append(f"alternatives[{i}] needs timeslot_id and room_id strings")
    return issues


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    req = json.load(open(sys.argv[1]))
    resp = json.load(open(sys.argv[2]))
    problems = check_response(req, resp)
    for p in problems:
        print("x", p)
    print("interface OK" if not problems else f"{len(problems)} interface issue(s)")
    sys.exit(1 if problems else 0)
