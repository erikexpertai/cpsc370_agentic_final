"""Minimal example agent: shows the Protocol 1.0 contract, NOT a good scheduler.

generate_schedule places courses round-robin with no constraint checking, so
the provost dashboard will show hard-constraint violations. That is the
point: replace this with your own checker + LLM reasoning.
"""


def _envelope(request, status, result, warnings=None, errors=None):
    return {
        "protocol_version": "1.0",
        "request_id": request["request_id"],  # echo unchanged
        "unit": request["unit"],
        "status": status,                      # completed | partial | failed
        "result": result,
        "warnings": warnings or [],
        "errors": errors or [],
    }


def run_agent(request: dict) -> dict:
    op = request.get("operation")
    p = request.get("payload", {})

    if op == "generate_schedule":
        slots = [t["timeslot_id"] for t in p["timeslots"]]
        rooms = [r["room_id"] for r in p["rooms"]]
        schedule = []
        for i, c in enumerate(p["courses"]):
            schedule.append({
                "course_id": c["course_id"],
                "timeslot_id": slots[i % len(slots)],
                "room_id": rooms[i % len(rooms)],
                "rationale": ["Round-robin placeholder; no constraints checked."],
                "preference_score": 0.0,
            })
        return _envelope(request, "completed", {
            "schedule": schedule, "unresolved": [], "summary": "Naive round-robin schedule."},
            warnings=["example agent: hard constraints were not checked"])

    if op == "evaluate_change":
        return _envelope(request, "completed", {
            "decision": "accept", "reason": "Example agent accepts everything (no checks).",
            "impact_score": 0.5, "alternatives": []})

    if op == "repair_schedule":
        return _envelope(request, "failed", {}, errors=["repair_schedule not implemented in example agent"])

    return _envelope(request, "failed", {}, errors=[f"unknown operation {op!r}"])
