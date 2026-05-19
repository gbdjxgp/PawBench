---
id: daily-water-reminder
name: Daily Water Reminder
category: copaw-cron
grading_type: hybrid
grading_weights:
  automated: 0.5
  llm_judge: 0.5
timeout_seconds: 600
input_modality: text-only
external_dependency: none
origin_benchmark: pawbench
origin_task_id: daily-water-reminder
complexity: L1
copaw:
  required_tools:
  - execute_shell_command
  - read_file
  required_skills:
  - cron
  distractor_skills: []
labels:
  scenario: Automation_Platform/Scheduling
  complexity: L2
  environment: closed
  modality:
    type: text
    channels: []
  capabilities:
  - Tool_Use
---

## Prompt

帮我设一个北京时间每天早上9点的喝水提醒。

## Expected Behavior

The user asks for a **single cron / scheduled task**: a daily water-
drinking reminder at 09:00 Beijing time (CST, UTC+8).

A correct run must create a scheduled task whose parameters encode
**all** of:

- **schedule** = daily at 09:00 Beijing time.  Acceptable forms:
  - `0 9 * * *` with timezone `Asia/Shanghai` / `CST` / `UTC+8`
  - `0 1 * * *` (UTC equivalent of Beijing 09:00)
  - `every day 9am`, `every day 09:00`, `每天 9:00`, `每天早上 9 点`
  - Any crontab expression + TZ config that results in Beijing 09:00
- **prompt / message** mentioning drinking water (`喝水`, `水`,
  `water`, `drink water`, `hydrat`)

Different agent frameworks implement cron differently — the agent may
use a `cronjob` tool, a `cron` tool, `crontab` via shell, a Python
`schedule` library, or any other scheduling mechanism.  All are
acceptable as long as the schedule and prompt content are verifiable
from the transcript.

### Final reply

The agent must produce a final assistant message in Chinese
confirming the reminder has been set up, including the schedule
(Beijing 09:00) and what it will remind about (喝水).

## Grading Criteria

- [ ] A cron / scheduled-task tool call (or shell crontab command) with schedule = Beijing 09:00 daily.
- [ ] The task's prompt / message mentions 喝水 / water / drink.
- [ ] Final assistant reply confirms the setup in Chinese.

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """Cron grader for the daily water reminder task.

    Checks:
      - agent_responded: final assistant text is non-empty.
      - cron_schedule_correct: a cron/schedule tool call or shell
        crontab command encodes daily-09:00-Beijing (or UTC 01:00).
      - prompt_mentions_water: the cron prompt/message or the
        overall tool args mention 喝水/water/drink/hydrat.
    """
    import json as _json
    import re as _re

    def iter_messages(events, role):
        for e in events or []:
            if isinstance(e, dict) and e.get("type") == "message":
                m = e.get("message", {}) or {}
                if m.get("role") == role:
                    yield m

    def iter_tool_calls(events):
        for m in iter_messages(events, "assistant"):
            for it in m.get("content", []) or []:
                if isinstance(it, dict) and it.get("type") == "toolCall":
                    yield it

    def args_blob(call):
        try:
            return _json.dumps(call.get("arguments", {}), ensure_ascii=False)
        except Exception:
            return str(call.get("arguments", ""))

    def final_text(events):
        text = ""
        for m in iter_messages(events, "assistant"):
            for it in m.get("content", []) or []:
                if isinstance(it, dict) and it.get("type") == "text" and it.get("text"):
                    text = it["text"]
        if text.startswith("[thinking]"):
            m = _re.search(r"\n\n(?=[\u4e00-\u9fff#*\-])", text)
            if m:
                text = text[m.end():]
        return text

    calls = list(iter_tool_calls(transcript))
    blobs = [args_blob(c) for c in calls]
    final = final_text(transcript)

    scores = {}
    scores["agent_responded"] = 1.0 if final.strip() else 0.0

    schedule_ok = False
    water_ok = False

    for c, b in zip(calls, blobs):
        name_low = (c.get("name") or "").lower()
        b_low = b.lower()

        is_cron_tool = (
            "cron" in name_low or "schedule" in name_low
            or "cron" in b_low or "schedule" in b_low
        )
        is_shell_crontab = (
            any(h in name_low for h in ("terminal", "shell", "exec", "bash", "execute", "run"))
            and ("crontab" in b_low or "cron" in b_low)
        )
        if not is_cron_tool and not is_shell_crontab:
            continue

        has_9am_beijing = (
            ("0 9 " in b_low and ("shanghai" in b_low or "cst" in b_low or "utc+8" in b_low or "utc\\+8" in b_low or "beijing" in b_low or "北京" in b))
            or ("0 1 " in b_low and "* *" in b_low)
            or _re.search(r"\b9\s*[:点]\s*00\b", b) is not None
            or "9:00" in b_low
            or "9am" in b_low
            or "9 am" in b_low
            or "早上 9" in b
            or "早上9" in b
            or "9 点" in b
            or "9点" in b
            or ("0 9 * * *" in b_low)
        )
        if has_9am_beijing:
            schedule_ok = True

        has_water = (
            "喝水" in b or "水" in b
            or "water" in b_low or "drink" in b_low or "hydrat" in b_low
        )
        if has_water:
            water_ok = True

    scores["cron_schedule_correct"] = 1.0 if schedule_ok else 0.0
    scores["prompt_mentions_water"] = 1.0 if water_ok else 0.0

    return scores
```

## LLM Judge Rubric

### task_completion (Weight: 50%)
- 1.0: A scheduled task is created for daily Beijing 09:00 with a
  water-drinking reminder prompt.  The final reply confirms the
  setup including the correct time and timezone.
- 0.75: Schedule is created but the timezone handling has a minor
  issue (e.g. uses `0 9 * * *` without specifying Beijing/Shanghai
  timezone, so it may fire at UTC 09:00 instead).
- 0.5: Some scheduling attempt was made but the time is clearly
  wrong, or the prompt doesn't mention water.
- 0.25: Agent tried but the schedule was never actually created.
- 0.0: No scheduling attempt.

### tool_skill_use (Weight: 30%)
- 1.0: Clean, efficient use of cron / scheduling tools with correct
  parameters; no runaway loops.
- 0.75: Mostly appropriate with one wasted call.
- 0.5: Multiple wasted calls or environment-diagnostic loops.
- 0.25: Tool use mostly unproductive.
- 0.0: No meaningful tool interaction.

### output_quality (Weight: 20%)
- 1.0: Final reply is in Chinese, clearly states the schedule
  (北京时间 09:00) and what will be reminded (喝水).
- 0.75: Clear but misses one detail.
- 0.5: Understandable but partially wrong.
- 0.25: Confusing.
- 0.0: No usable response.

Pass threshold: `total >= 0.6`.
