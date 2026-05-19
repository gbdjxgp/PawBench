---
id: 01_Productivity_Flow_task_6_calendar_scheduling
name: Calendar Conflict Detection and Smart Scheduling
category: 01_Productivity_Flow
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.8
  llm_judge: 0.2
workspace_files:
- source: assets/T141_wildclawbench_01_calendar_scheduling/01_calendar_scheduling/calendar.ics
  dest: calendar.ics
- source: assets/T141_wildclawbench_01_calendar_scheduling/01_calendar_scheduling/meeting_requests.json
  dest: meeting_requests.json
- source: assets/T141_wildclawbench_01_calendar_scheduling/01_calendar_scheduling/constraints.yaml
  dest: constraints.yaml
- source: assets/T141_wildclawbench_01_calendar_scheduling/01_calendar_scheduling/gt/optimal_unscheduled.json
  dest: gt/optimal_unscheduled.json
labels:
  complexity: L3
  environment: closed
  modality:
    type: text
    channels: []
  scenario: Office_Productivity/Calendar
  capabilities:
  - Logic_Reasoning
  - Tool_Use
  - Planning
  - Self_Verification
---
## Prompt

I manage a busy team calendar and need help resolving scheduling conflicts.

Please optimize the weekly schedule using the provided files in the working directory:

- `calendar.ics`: an existing calendar containing 5 scheduled events
- `meeting_requests.json`: 8 new meeting requests, each with:
  - `id`
  - `title`
  - `preferred_windows`
  - `duration_minutes`
  - `priority`
  - `required_attendees`
  - `optional_attendees`
- `constraints.yaml`: scheduling rules such as:
  - no meetings during lunch break `12:00-13:00`
  - each attendee can have at most 4 meetings per day
  - some attendees may be unavailable on certain weekdays
  - additional hard or soft constraints may be included

Your job:

1. Read the existing calendar and detect time conflicts.
2. Schedule as many new meeting requests as possible while respecting all hard constraints.
3. Prefer higher-priority meetings when not all requests can be scheduled.
4. If a request cannot be scheduled, explain the main reason clearly.
5. Save the results into `output/` with the following files:
   - `output/scheduled.ics`
   - `output/unscheduled.json`
   - `output/decision_log.md`

### `scheduled.ics`

- Must be a valid iCalendar file
- Must include all original events from `calendar.ics`
- Must add newly scheduled meetings as `VEVENT`s

### `unscheduled.json`

A JSON array. Each unscheduled item must contain `id`, `title`, `reason_code`, `reason_text`.

### `decision_log.md`

Use exactly the following structure:

```
### Scheduling Decision Log

### Summary
- Total requests: 8
- Scheduled: <number>
- Unscheduled: <number>
- Total priority weight achieved: <number>

### High Priority Decisions
- Explain important trade-offs, especially when a lower-priority meeting was dropped in favor of a higher-priority one.

### Unscheduled Requests
- `req_xxx` — concise explanation
```

Important rules:

- Do not delete or modify original calendar events.
- Do not create any other files or directories.
- Required attendees must all be available for a meeting to be scheduled.
- Lunch break, per-day meeting cap, and attendee unavailability are hard constraints.
- If multiple valid schedules exist, prefer the one with the highest total scheduled priority weight.

## Expected Behavior

The agent should:

1. Parse `calendar.ics` and recover all 5 existing events
2. Parse `meeting_requests.json` and `constraints.yaml`
3. Detect conflicts and produce a valid `output/scheduled.ics` (5 originals + N new)
4. Produce `output/unscheduled.json` with structured reasons (e.g., req_004 lunch violation, req_006 Carol Friday unavailable)
5. Produce `output/decision_log.md` with summary

## Grading Criteria

- [ ] All three output files created
- [ ] scheduled.ics preserves all 5 original events
- [ ] No scheduled meeting violates lunch break, attendee availability, daily cap, or preferred windows
- [ ] No required attendee is missing from any scheduled meeting
- [ ] unscheduled.json includes valid `reason_code`
- [ ] If hard constraints satisfied, score ∝ optimality ratio against ground-truth optimum

## Automated Checks

```python
import json
import re
from collections import Counter
from datetime import datetime, time, timezone
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    """Calendar scheduling grader, ported from WildClawBench task 1.6.

    Same evaluation target: file validity → hard-constraint satisfaction → optimality.
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    ALL_CRITERIA = [
        "output_files_valid",
        "scheduled_ics_parseable",
        "preserve_original_events",
        "unscheduled_json_valid",
        "decision_log_exists",
        "request_coverage_consistent",
        "required_attendees_respected",
        "duration_respected",
        "within_preferred_windows",
        "no_lunch_violation",
        "no_attendee_conflicts",
        "daily_limit_respected",
        "attendee_unavailability_respected",
        "reason_codes_valid",
        "hard_constraint_pass",
        "optimality_ratio",
        "overall_score",
    ]
    scores = {k: 0.0 for k in ALL_CRITERIA}

    workspace = Path(workspace_path)
    src_calendar = workspace / "calendar.ics"
    meeting_requests_path = workspace / "meeting_requests.json"
    constraints_path = workspace / "constraints.yaml"
    output_dir = workspace / "output"
    scheduled_calendar = output_dir / "scheduled.ics"
    unscheduled_path = output_dir / "unscheduled.json"
    decision_log = output_dir / "decision_log.md"
    optimal_unscheduled = workspace / "gt" / "optimal_unscheduled.json"

    if not (src_calendar.exists() and meeting_requests_path.exists()
            and constraints_path.exists() and scheduled_calendar.exists()
            and unscheduled_path.exists() and decision_log.exists()):
        return {"overall_score": 0.0}

    calendar_text = scheduled_calendar.read_text(errors="ignore")
    source_text = src_calendar.read_text(errors="ignore")
    constraints_text = constraints_path.read_text(errors="ignore")

    def normalize_text(t):
        return re.sub(r"\s+", " ", str(t or "")).strip()

    def unfold_ics_lines(text):
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        out = []
        for line in text.split("\n"):
            if line.startswith((" ", "\t")) and out:
                out[-1] += line[1:]
            else:
                out.append(line)
        return out

    def parse_ics_property(line):
        if ":" not in line:
            return None
        head, value = line.split(":", 1)
        parts = head.split(";")
        name = parts[0].strip().upper()
        params = {}
        for part in parts[1:]:
            if "=" in part:
                k, v = part.split("=", 1)
                params[k.strip().upper()] = v.strip().strip('"')
        return {"name": name, "params": params, "value": value.strip()}

    def parse_ics_datetime(prop, default_tz):
        if not prop:
            return None
        value = str(prop.get("value", "")).strip()
        params = prop.get("params", {}) or {}
        value_type = str(params.get("VALUE", "")).upper()
        tzid = params.get("TZID")
        # All-day DATE values: treat as midnight in local tz
        if value_type == "DATE":
            try:
                return datetime.strptime(value, "%Y%m%d").replace(tzinfo=default_tz)
            except ValueError:
                return None
        if value.endswith("Z"):
            try:
                return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        tzinfo = default_tz
        if tzid:
            try:
                tzinfo = ZoneInfo(str(tzid))
            except Exception:
                pass
        for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=tzinfo)
            except ValueError:
                pass
        return None

    def parse_iso_dt(value):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None

    def parse_hhmm(value):
        try:
            hh, mm = value.split(":")
            return time(int(hh), int(mm))
        except Exception:
            return None

    def normalize_attendee(raw):
        return raw.replace("mailto:", "").replace("MAILTO:", "").strip().lower()

    def parse_ics_events(text, default_tz):
        events = []
        cur = None
        nested_depth = 0
        for line in unfold_ics_lines(text):
            stripped = line.strip()
            up = stripped.upper()
            if up == "BEGIN:VEVENT":
                cur = []
                nested_depth = 0
                continue
            if cur is None:
                continue
            if up.startswith("BEGIN:"):
                nested_depth += 1
                continue
            if up.startswith("END:"):
                component = up[4:]
                if component == "VEVENT" and nested_depth == 0:
                    pmap = {}
                    for p in cur:
                        pmap.setdefault(p["name"], []).append(p)
                    start_p = (pmap.get("DTSTART") or [None])[0]
                    end_p = (pmap.get("DTEND") or [None])[0]
                    attendees = [normalize_attendee(p["value"]) for p in pmap.get("ATTENDEE", [])]
                    desc = (pmap.get("DESCRIPTION") or [{"value": ""}])[0]["value"]
                    events.append({
                        "uid": (pmap.get("UID") or [{"value": ""}])[0]["value"],
                        "summary": (pmap.get("SUMMARY") or [{"value": ""}])[0]["value"].strip(),
                        "description": desc.strip(),
                        "attendees": attendees,
                        "start_dt": parse_ics_datetime(start_p, default_tz),
                        "end_dt": parse_ics_datetime(end_p, default_tz),
                    })
                    cur = None
                    nested_depth = 0
                    continue
                nested_depth = max(0, nested_depth - 1)
                continue
            prop = parse_ics_property(stripped)
            if prop is not None:
                cur.append(prop)
        return events

    def event_fingerprint(e):
        if not e.get("start_dt") or not e.get("end_dt"):
            return None
        return (
            normalize_text(e["summary"]).casefold(),
            e["start_dt"].astimezone(timezone.utc).isoformat(),
            e["end_dt"].astimezone(timezone.utc).isoformat(),
            tuple(sorted(e["attendees"])),
        )

    def parse_simple_constraints(text):
        result = {
            "timezone": "UTC", "lunch_start": None, "lunch_end": None,
            "max_per_day": None, "schedule_only_within_preferred_windows": False,
            "require_all_required_attendees": False,
            "allowed_reason_codes": set(), "attendee_unavailability": {},
        }
        section = None
        cur_attendee = cur_weekday = cur_window = None
        for raw in text.splitlines():
            line = raw.rstrip()
            stripped = line.strip()
            if not stripped:
                continue
            m = re.match(r"timezone:\s*([^\s]+)", stripped)
            if m:
                result["timezone"] = m.group(1)
                continue
            if stripped == "hard_constraints:":
                section = "hard_constraints"; continue
            if stripped == "attendee_unavailability:":
                section = "attendee_unavailability"; cur_attendee = None; continue
            if stripped == "allowed_reason_codes:":
                section = "allowed_reason_codes"; continue
            if section == "hard_constraints":
                m = re.match(r'start:\s*"([^"]+)"', stripped)
                if m and result["lunch_start"] is None:
                    result["lunch_start"] = parse_hhmm(m.group(1)); continue
                m = re.match(r'end:\s*"([^"]+)"', stripped)
                if m and result["lunch_end"] is None:
                    result["lunch_end"] = parse_hhmm(m.group(1)); continue
                m = re.match(r"max_meetings_per_attendee_per_day:\s*(\d+)", stripped)
                if m:
                    result["max_per_day"] = int(m.group(1)); continue
                m = re.match(r"schedule_only_within_preferred_windows:\s*(true|false)", stripped)
                if m:
                    result["schedule_only_within_preferred_windows"] = m.group(1) == "true"; continue
                m = re.match(r"require_all_required_attendees:\s*(true|false)", stripped)
                if m:
                    result["require_all_required_attendees"] = m.group(1) == "true"; continue
            if section == "attendee_unavailability":
                m = re.match(r"([^\s][^:]+):\s*$", stripped)
                if m:
                    cur_attendee = m.group(1)
                    result["attendee_unavailability"].setdefault(cur_attendee, [])
                    cur_weekday = None; cur_window = None
                    continue
                m = re.match(r"-\s*weekday:\s*(\w+)", stripped)
                if m and cur_attendee:
                    cur_weekday = m.group(1); cur_window = None; continue
                m = re.match(r'start:\s*"([^"]+)"', stripped)
                if m and cur_attendee and cur_weekday:
                    cur_window = {"start": parse_hhmm(m.group(1))}; continue
                m = re.match(r'end:\s*"([^"]+)"', stripped)
                if m and cur_attendee and cur_weekday and cur_window:
                    cur_window["end"] = parse_hhmm(m.group(1))
                    result["attendee_unavailability"][cur_attendee].append(
                        {"weekday": cur_weekday, "start": cur_window["start"], "end": cur_window["end"]})
                    cur_window = None; continue
            if section == "allowed_reason_codes":
                m = re.match(r"-\s*(\S+)", stripped)
                if m:
                    result["allowed_reason_codes"].add(m.group(1))
        return result

    try:
        unscheduled_items = json.loads(unscheduled_path.read_text())
        scores["unscheduled_json_valid"] = 1.0 if isinstance(unscheduled_items, list) else 0.0
    except Exception:
        return {"overall_score": 0.0}

    scores["decision_log_exists"] = 1.0 if len(decision_log.read_text().strip()) > 50 else 0.0

    try:
        requests = json.loads(meeting_requests_path.read_text())
    except Exception:
        return {"overall_score": 0.0}

    constraints = parse_simple_constraints(constraints_text)
    try:
        local_tz = ZoneInfo(constraints["timezone"])
    except Exception:
        local_tz = timezone.utc
    valid_reason_codes = constraints["allowed_reason_codes"] or {
        "attendee_unavailable", "time_conflict", "daily_limit_exceeded",
        "outside_preferred_window", "lower_priority_than_competing_request",
        "insufficient_duration_slot", "no_lunch_violation", "unknown",
    }

    scheduled_events = parse_ics_events(calendar_text, local_tz)
    original_events = parse_ics_events(source_text, local_tz)
    scores["scheduled_ics_parseable"] = (
        1.0 if "BEGIN:VCALENDAR" in calendar_text and "END:VCALENDAR" in calendar_text
        and len(scheduled_events) >= len(original_events) > 0 else 0.0)
    scores["output_files_valid"] = 1.0 if (scores["scheduled_ics_parseable"]
        and scores["unscheduled_json_valid"] and scores["decision_log_exists"]) else 0.0

    if not scores["scheduled_ics_parseable"]:
        return {"overall_score": 0.0}

    request_by_title = {normalize_text(r["title"]).casefold(): r for r in requests if isinstance(r, dict) and r.get("title")}
    request_by_id = {normalize_text(r["id"]).casefold(): r for r in requests if isinstance(r, dict) and r.get("id")}

    def match_request(event):
        s = normalize_text(event.get("summary", "")).casefold()
        if s in request_by_title:
            return request_by_title[s]
        u = normalize_text(event.get("uid", "")).casefold()
        for rid, req in request_by_id.items():
            if rid and rid in u:
                return req
        # Fallback: description may embed the request id
        desc = normalize_text(event.get("description", "")).casefold()
        for rid, req in request_by_id.items():
            if rid and rid in desc:
                return req
        return None

    original_counts = Counter(fp for fp in (event_fingerprint(e) for e in original_events) if fp)
    scheduled_counts = Counter(fp for fp in (event_fingerprint(e) for e in scheduled_events) if fp)
    scores["preserve_original_events"] = (
        1.0 if original_counts and all(scheduled_counts[fp] >= n for fp, n in original_counts.items()) else 0.0)

    remaining = original_counts.copy()
    new_events = []
    for e in scheduled_events:
        fp = event_fingerprint(e)
        if fp and remaining[fp] > 0:
            remaining[fp] -= 1
        else:
            new_events.append(e)

    new_event_by_request_id = {}
    for e in new_events:
        req = match_request(e)
        if req and req.get("id"):
            new_event_by_request_id[req["id"]] = e

    attendee_intervals = {}
    for e in scheduled_events:
        if not e.get("start_dt") or not e.get("end_dt"):
            continue
        for a in e["attendees"]:
            attendee_intervals.setdefault(a, []).append((e["start_dt"], e["end_dt"]))
    conflicts = 0
    for ints in attendee_intervals.values():
        ints.sort()
        for i in range(1, len(ints)):
            if ints[i][0] < ints[i - 1][1]:
                conflicts += 1
    scores["no_attendee_conflicts"] = 1.0 if conflicts == 0 else 0.0

    daily = {}
    for e in scheduled_events:
        if not e.get("start_dt"):
            continue
        date_key = e["start_dt"].astimezone(local_tz).date().isoformat()
        for a in e["attendees"]:
            daily[(a, date_key)] = daily.get((a, date_key), 0) + 1
    max_per_day = constraints["max_per_day"] or 4
    scores["daily_limit_respected"] = (
        1.0 if (daily and all(v <= max_per_day for v in daily.values())) else 0.0
    )

    required_ok = duration_ok = lunch_ok = unavailable_ok = preferred_ok = True
    lunch_start = constraints["lunch_start"] or time(12, 0)
    lunch_end = constraints["lunch_end"] or time(13, 0)
    for e in new_events:
        req = match_request(e)
        sd, ed = e.get("start_dt"), e.get("end_dt")
        if not req or not sd or not ed:
            required_ok = duration_ok = lunch_ok = unavailable_ok = preferred_ok = False
            continue
        if isinstance(req.get("required_attendees"), list):
            req_att = {x.strip().lower() for x in req["required_attendees"]}
            if not req_att.issubset(set(e["attendees"])):
                required_ok = False
        if int((ed - sd).total_seconds() // 60) != int(req.get("duration_minutes", 0)):
            duration_ok = False
        ls = sd.astimezone(local_tz)
        le = ed.astimezone(local_tz)
        ls_dt = ls.replace(hour=lunch_start.hour, minute=lunch_start.minute, second=0, microsecond=0)
        le_dt = ls.replace(hour=lunch_end.hour, minute=lunch_end.minute, second=0, microsecond=0)
        if ls < le_dt and le > ls_dt:
            lunch_ok = False
        weekday = ls.strftime("%A")
        st, et = ls.time(), le.time()
        for a in e["attendees"]:
            for rule in constraints["attendee_unavailability"].get(a, []):
                if rule["weekday"] != weekday:
                    continue
                rs = rule["start"] or time(0, 0)
                re_ = rule["end"] or time(23, 59)
                if st < re_ and et > rs:
                    unavailable_ok = False

        if constraints["schedule_only_within_preferred_windows"]:
            within_any = False
            for window in req.get("preferred_windows", []) or []:
                w_start = parse_iso_dt(str(window.get("start", "")))
                w_end = parse_iso_dt(str(window.get("end", "")))
                if not w_start or not w_end:
                    continue
                s_utc = sd.astimezone(timezone.utc)
                e_utc = ed.astimezone(timezone.utc)
                ws = w_start.astimezone(timezone.utc) if w_start.tzinfo else w_start.replace(tzinfo=timezone.utc)
                we = w_end.astimezone(timezone.utc) if w_end.tzinfo else w_end.replace(tzinfo=timezone.utc)
                if s_utc >= ws and e_utc <= we:
                    within_any = True
                    break
            if not within_any:
                preferred_ok = False

    scores["required_attendees_respected"] = 1.0 if required_ok else 0.0
    scores["duration_respected"] = 1.0 if duration_ok else 0.0
    scores["within_preferred_windows"] = 1.0 if preferred_ok else 0.0
    scores["no_lunch_violation"] = 1.0 if lunch_ok else 0.0
    scores["attendee_unavailability_respected"] = 1.0 if unavailable_ok else 0.0

    scheduled_ids = set(new_event_by_request_id.keys())
    unscheduled_ids = set()
    reason_ok = isinstance(unscheduled_items, list)
    for item in unscheduled_items if reason_ok else []:
        if not isinstance(item, dict) or not item.get("id"):
            reason_ok = False; break
        unscheduled_ids.add(item["id"])
        if item.get("reason_code") not in valid_reason_codes:
            reason_ok = False; break
    scores["reason_codes_valid"] = 1.0 if reason_ok else 0.0

    request_ids = {item["id"] for item in requests if isinstance(item, dict) and item.get("id")}
    dup_schedule = False
    seen_req = set()
    for e in new_events:
        req = match_request(e)
        if req and req.get("id"):
            rid = req["id"]
            if rid in seen_req:
                dup_schedule = True
                break
            seen_req.add(rid)
    scores["request_coverage_consistent"] = 1.0 if (
        reason_ok
        and scheduled_ids.isdisjoint(unscheduled_ids)
        and scheduled_ids | unscheduled_ids == request_ids
        and not dup_schedule
    ) else 0.0

    hard_keys = ["output_files_valid", "scheduled_ics_parseable", "preserve_original_events",
                 "unscheduled_json_valid", "decision_log_exists", "request_coverage_consistent",
                 "required_attendees_respected", "duration_respected", "within_preferred_windows",
                 "no_lunch_violation", "no_attendee_conflicts",
                 "daily_limit_respected", "attendee_unavailability_respected",
                 "reason_codes_valid"]
    hard_pass = all(scores[k] == 1.0 for k in hard_keys)
    scores["hard_constraint_pass"] = 1.0 if hard_pass else 0.0

    if not hard_pass:
        scores["optimality_ratio"] = 0.0
        scores["overall_score"] = 0.0
        return {"overall_score": 0.0}

    priority_weight = {"P0": 5, "P1": 3, "P2": 1}
    achieved = sum(priority_weight.get(str(r.get("priority", "")).strip(), 1)
                   for r in requests if isinstance(r, dict) and r.get("id") in scheduled_ids)
    optimal_ids = set()
    if optimal_unscheduled.exists():
        try:
            opt_un = json.loads(optimal_unscheduled.read_text())
            optimal_ids = request_ids - {item["id"] for item in opt_un if isinstance(item, dict) and item.get("id")}
        except Exception:
            pass
    optimal_weight = sum(priority_weight.get(str(r.get("priority", "")).strip(), 1)
                         for r in requests if isinstance(r, dict) and r.get("id") in optimal_ids)
    scores["optimality_ratio"] = round(achieved / optimal_weight, 4) if optimal_weight else 0.0
    scores["overall_score"] = scores["optimality_ratio"]
    return {"overall_score": float(scores["overall_score"])}
```

## LLM Judge Rubric

### Criterion 1: Constraint Reasoning Quality (Weight: 60%)

Evaluate whether the agent demonstrated clear reasoning about scheduling constraints:

**Scoring:**
- **1.0**: Explicitly identified lunch break, attendee unavailability (Carol Friday), max-per-day cap; explained why each rejected request was rejected with the correct reason code.
- **0.7–0.8**: Identified most constraints but missed one (e.g., didn't mention Carol's Friday unavailability).
- **0.4–0.6**: Identified only basic conflicts; reasoning shallow.
- **0.0–0.3**: No constraint reasoning visible.

### Criterion 2: Output Format Compliance (Weight: 40%)

**Scoring:**
- **1.0**: scheduled.ics, unscheduled.json (valid reason codes), decision_log.md all match the required structure.
- **0.6–0.8**: Output files present but with minor format issues (e.g., missing reason_code in some unscheduled items).
- **0.0–0.4**: Major format violations or missing files.
