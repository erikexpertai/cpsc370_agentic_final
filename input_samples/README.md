# Input samples

These are real requests, exactly as the provost sends them to a unit agent
during a run. Each one is paired with a schema-compliant response from the
provost's reference agent.

The responses show **format**, not ideal decisions. Your agent should
explain itself better than the reference agent does.

The table of what each sample covers is in [INDEX.md](INDEX.md).

| File | What it is |
|---|---|
| `NN_<situation>.request.json` | The dict passed to your `run_agent(request)` |
| `NN_<situation>.response.json` | An example of a valid dict to return |

## What to notice

- **Every payload carries the full envelope.** That's `courses`, `timeslots`,
  `rooms`, `faculty_constraints`, `global_constraints` and `context`, on
  every operation, not only `generate_schedule`. Your agent can be
  stateless.
- **The envelope changes during a run.** Compare `rooms` in
  `06_repair_room_unavailable` with `01_generate_schedule`: the closed room
  is gone. In `11_repair_escalation_room_reservation`, the room is still
  there but has `unavailable_times`. Always trust the current request.
- **`evaluate_change.payload.reason`** names the conflict and the other
  unit's course that holds the resource. For example: `Resolve shared room
  AF-206A: CES LEAD-310-02 holds TR-1130/AF-206A.` Your alternatives must
  not land back on that resource at that time.
- **Rejecting.** See `05_evaluate_change_rejected_with_alternatives`. The
  rejection names the specific preference that caused it, and every
  alternative is feasible. The course's current placement is never offered
  as an alternative, because that placement *is* the conflict.
- **Escalations** (`11`, `12`) are ordinary `repair_schedule` requests. The
  provost sends one when a conflict can't be settled by moving a single
  course. You may need to move *other* courses to satisfy the new
  constraint. `course_must_move` with every slot but one forbidden
  effectively pins the course to the remaining slot.
- **`request_id`s** here start with `run-SAMPLE`. In a live run they're
  unique per request, and you must echo them unchanged.

## Using them in tests

```python
import json
from agent import run_agent

req = json.load(open("input_samples/01_generate_schedule.request.json"))
resp = run_agent(req)
assert resp["request_id"] == req["request_id"]
```

To check interface compliance the same way the provost does:

```python
import sys; sys.path.insert(0, "student_kit")
from check_response import check_response

issues = check_response(req, resp)  # [] means compliant
```

Checking hard constraints is part of your agent, so build your own checker
and test it against these samples. In a practice run, the provost reports
any violations it finds in `outputs/<run>/messages.jsonl`
(`"type": "hard_constraint_check"`).

## Regenerating

These samples are derived from `data/practice/`, and instructor IDs are
pseudonyms. The instructor regenerates them whenever the envelopes or the
provost change.
