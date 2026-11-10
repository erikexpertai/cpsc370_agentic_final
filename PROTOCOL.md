# Protocol 1.0: addendum to the project spec

The project spec defines the request and response envelopes and the three
operations. This addendum pins down the details the provost relies on.
Everything here is **additive**: a response that follows the spec exactly is
still compliant.

## 1. Connecting

Your agent does not run a server. Run `student_kit/connect.py`, which dials
out to the provost, receives requests, calls your `agent.run_agent(request)`,
and returns the dict you produce.

| | Provost URL |
|---|---|
| Practice (your laptop) | `http://localhost:8370` (the Docker container) |
| Final integration | `http://<instructor-ip>:8370` (announced in class) |

`--unit` takes your unit code: `SBE CES COPA CHBS CFMA SENG SOL COS SOC SOP CHSS`.

## 2. Every payload carries your full resource envelope

`generate_schedule`, `evaluate_change`, and `repair_schedule` all include
`courses`, `timeslots`, `rooms`, `faculty_constraints`, `global_constraints`
and `context`, in addition to the operation-specific fields. Your agent can
be stateless.

The envelope can **change during a run**. Disruptions and provost
reservations (§6) are written into it. Always use the envelope in the
current request, never a cached copy.

## 3. Time semantics

Day codes are `M T W R F` (`R` is Thursday). **Two timeslots conflict if they
share a day and their clock intervals overlap, even if their IDs differ.**
For example, `MWF-1000` (10:00–10:50) overlaps `MW-1000` (10:00–11:15).

## 4. Additional fields you may see

| Where | Field | Meaning |
|---|---|---|
| `rooms[]` | `unavailable_times: [timeslot_id]` | **Hard.** The room can't be used at any slot overlapping these. |
| `rooms[]` | `shared: bool` | Other units also hold this room. You may want to prefer non-shared rooms. |
| `rooms[]` | `building` | Informational. |
| `faculty_constraints[]` | `unavailable_times` | **Hard** (as in the spec). Overlap semantics apply. |

## 5. `global_constraints` types

```json
{"type": "blackout", "days": ["W"], "start": "12:00", "end": "13:00"}
{"type": "forbidden_timeslots", "course_id": "CPSC-350-01", "timeslot_ids": ["MW-1000"]}
{"type": "cross_list_match", "rule": "same_timeslot", "owner": "<unit name>",
 "courses": [{"unit": "<unit A>", "course_id": "..."}, {"unit": "<unit B>", "course_id": "..."}]}
```

- `blackout` and `forbidden_timeslots` are hard constraints.
- `cross_list_match` means the two courses are one combined class taught
  across units. They must end up at the same timeslot. You can't see the
  other unit's placement during `generate_schedule`. The provost aligns the
  pair afterwards, by asking you through `evaluate_change`, or by sending a
  `repair_schedule` with a `course_must_move` disruption.

## 6. Disruptions (`repair_schedule.payload.disruptions[]`)

| type | fields |
|---|---|
| `room_unavailable` | `room_id`, optional `timeslot_ids`. Without `timeslot_ids`, the room is gone entirely. |
| `room_capacity_change` | `room_id`, `new_capacity` |
| `faculty_unavailable` | `instructor_id`, `timeslot_ids` |
| `enrollment_change` | `course_id`, `new_enrollment` |
| `blackout` | `days`, `start`, `end` |
| `course_must_move` | `course_id`, `forbidden_timeslot_ids` |

The envelope in the same request **already reflects** the disruption. The
`disruptions` list tells you *why* things changed.

The provost also uses `repair_schedule` to settle a conflict it couldn't
resolve by moving a single course. It then reserves a room or instructor
time for another unit, sends the reservation as a disruption, and expects
your repair to work around it.

## 7. Semantics

- **`accept` is not a commit.** Only the provost commits changes. You see the
  outcome in the next request's `current_schedule`.
- **`current_schedule[]`** items have the same shape as
  `generate_schedule.result.schedule[]`. Only `course_id`, `timeslot_id` and
  `room_id` are guaranteed.
- **Unresolved items** can be strings (course IDs) or objects
  `{"course_id": ..., "reason": ...}`. The provost accepts both.
- **Timeouts:** `generate_schedule` 180 s, `evaluate_change` 60 s,
  `repair_schedule` 180 s. A timeout counts as a failed response.
- **Idempotency:** `request_id`s are unique per run. Echo them unchanged.

## 8. How the provost scores you

These are computed by the provost and shown live on the dashboard.

| Metric | How it's measured |
|---|---|
| Interface compliance | % of your responses that pass the schema checks in `student_kit/check_response.py` (identical to the provost's). |
| Hard-constraint compliance | % of returned schedules with zero violations. The provost re-checks every one. Violating entries are dropped and the course counts as unresolved. Details are in `messages.jsonl` (`"type": "hard_constraint_check"`). |
| Task completion | % of responses with status `completed` or `partial` and a usable result. |
| Alternative validity | % of alternatives you offer on rejection that are feasible in your own envelope. The share that is also free university-wide is shown in parentheses (informational). |
| Repair stability | Courses changed minus courses that had to change, averaged over repairs. Lower is better. |
| Silently dropped | Courses missing from your schedule that you didn't list in `unresolved`. This should always be 0. |
