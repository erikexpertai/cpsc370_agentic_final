# CPSC370: Chapman Agentic Scheduling Challenge

Everything you need to build and test your academic-unit agent against the
**provost orchestrator**, the university coordinator that all 11 unit agents
work with.

- **[Project spec (v1.1)](spec/CPSC370_Final_Project_Spec.pdf).** Start here.
- **[Protocol 1.0 quick reference](PROTOCOL.md):** fields, constraint types,
  disruptions, and how you're scored.
- **[Input samples](input_samples/):** real requests your agent will receive,
  each with a valid example response.

```
student_kit/       connect.py (links your agent to the provost), check_response.py, example_agent.py
input_samples/     12 captured requests + example responses
data/practice/     practice envelopes for all 11 units + the practice disruption scenario
docker-compose.yml runs the practice provost (prebuilt image)
spec/              project specification
```

## Practice on your laptop

You need Docker Desktop and Python 3.9+. Nothing else is installed: the
connector uses only the Python standard library.

1. **Start the provost:**

   ```bash
   docker compose up
   ```

   Open <http://localhost:8370>. That's the live dashboard.

2. **Connect your agent** in another terminal. Use your unit code: `SBE CES COPA
   CHBS CFMA SENG SOL COS SOC SOP CHSS`.

   ```bash
   python student_kit/connect.py --unit SENG --agent path/to/your/agent.py --team "Team Name"
   ```

   To see the plumbing work before you have an agent, try
   `--agent student_kit/example_agent.py`. It's deliberately naive, so the
   dashboard will show its violations.

3. **Click Start run** on the dashboard. Your agent receives:
   - `generate_schedule`
   - `evaluate_change` whenever your unit collides with another unit
   - `repair_schedule` after each disruption

   Reference agents play the other 10 units.

4. **Read the results** under `outputs/<run-id>/`, also linked from the
   dashboard:
   - `final_schedule.csv`
   - `metrics.json`: the same metrics the spec grades
   - `moves.json`
   - `messages.jsonl`: every request and response, plus a
     `"type": "hard_constraint_check"` record listing exactly which hard
     constraints any returned schedule broke

### Useful tools

- **Your envelope**, to develop offline:

  ```bash
  python student_kit/connect.py envelope --unit SENG --out envelope.json
  ```

- **Interface check**, the same schema checks the provost runs:

  ```bash
  python student_kit/check_response.py request.json response.json
  ```

- **Capture traffic** for test cases: add `--save-dir captured/` to `connect.py`.
- **Several units at once:** connect one agent per unit to the same provost.

## Final integration

Same command, pointed at the instructor's provost (address announced in class):

```bash
python student_kit/connect.py --unit SENG --agent path/to/your/agent.py --team "Team Name" \
    --provost http://<instructor-ip>:8370
```

Your laptop only makes outbound connections, so no firewall or port setup is
needed. Keep the terminal open until the instructor ends the run.

## Data

`data/practice/` is derived from Chapman's Fall 2026 registrar schedule:

- in-person sections only
- about 36 sections per unit
- instructor names removed, IDs replaced by pseudonyms `FAC-xxxxxx`

You may send this data to external LLM APIs. Don't attempt to re-identify
instructors. The integration-day envelopes have the same shape but contain
each unit's full section list.
