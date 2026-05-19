---
id: 069-cron-astock-report
name: Cron Astock Report
category: copaw-cron
grading_type: hybrid
grading_weights:
  automated: 0.5
  llm_judge: 0.5
timeout_seconds: 900
input_modality: text-only
external_dependency: none
origin_benchmark: pawbench
origin_task_id: 069-cron-astock-report
complexity: L2
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
  environment: open
  modality:
    type: text
  capabilities:
  - Tool_Use
---

## Prompt

现在是北京时区，每天早上10点帮我查一下A股主要指数的涨跌情况，生成一份简报发到控制台。

## Expected Behavior

The user asks for a **single cron / scheduled task** that:

1. Fires **daily at 10:00 Beijing time** (CST, UTC+8).
2. **Queries A-share main index data** (上证/深证/创业板 etc.) and
   generates a briefing.
3. **Delivers the output to the console** (控制台).

A correct run must create a scheduled task whose parameters encode
**all** of:

- **schedule** = daily at 10:00 Beijing time.  Acceptable forms:
  - `0 10 * * *` with timezone `Asia/Shanghai` / `CST` / `UTC+8`
  - `0 2 * * *` (UTC equivalent of Beijing 10:00)
  - `0 2 * * 1-5` (weekday-only variant — acceptable since A-shares
    only trade on weekdays; treating this as a smart interpretation)
  - `every day 10am`, `每天 10:00`, `每天早上 10 点`
- **prompt / message** mentioning A-share index data — at least one
  of: `A股`, `指数`, `涨跌`, `股市`, `a-share`, `index`
- **delivery** = console.  Acceptable forms:
  - `channel=console`, `deliver=console`, `"deliver":"console:..."`
  - `deliver=origin` (hermes convention — delivers to the
    originating session, which is the console)
  - For shell-based crontab, output going to stdout / a log file
    that gets displayed is acceptable (console is implied for
    crontab output).

### Final reply

The agent must produce a final assistant message in Chinese
confirming the cron setup, including the schedule (北京时间 10:00)
and what it will do (查 A 股指数 + 生成简报).

## Grading Criteria

- [ ] A cron / scheduled-task tool call with schedule = Beijing 10:00 daily (or weekdays).
- [ ] The task's prompt / message mentions A-share / index data.
- [ ] Delivery is configured for console (or implied by crontab stdout).
- [ ] Final assistant reply confirms the setup in Chinese.

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """Cron grader for the A-stock daily report task.

    Checks:
      - agent_responded: final assistant text is non-empty.
      - cron_schedule_correct: a cron/schedule tool call or shell
        crontab command encodes daily-10:00-Beijing (or UTC 02:00).
      - prompt_mentions_astock: ANY tool call (not just cron calls)
        mentions A股/指数/涨跌/股市/a-share/index/stock.
        Shell-based agents write a Python script containing the
        A-stock logic, so we must search all tool calls.
      - delivery_console: delivery is set to console, or the mechanism
        is shell crontab (which implies console/stdout).
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

    EXEC_TOOL_HINTS = (
        "terminal", "shell", "exec", "bash", "run_command",
        "shell_exec", "execute_command", "run_shell", "execute",
    )

    calls = list(iter_tool_calls(transcript))
    blobs = [args_blob(c) for c in calls]
    final = final_text(transcript)

    scores = {}
    scores["agent_responded"] = 1.0 if final.strip() else 0.0

    schedule_ok = False
    astock_ok = False
    console_ok = False
    used_shell_crontab = False

    ASTOCK_TOKENS = (
        "a股", "A股", "指数", "涨跌", "股市", "a-share", "index",
        "上证", "深证", "创业板", "stock", "a_stock", "astock",
    )

    for c, b in zip(calls, blobs):
        name_low = (c.get("name") or "").lower()
        b_low = b.lower()

        has_astock = (
            any(tok in b for tok in ASTOCK_TOKENS)
            or any(tok.lower() in b_low for tok in ASTOCK_TOKENS)
        )
        if has_astock:
            astock_ok = True

        is_cron_tool = (
            "cron" in name_low or "schedule" in name_low
            or "cron" in b_low or "schedule" in b_low
        )
        is_shell_crontab = (
            any(h in name_low for h in EXEC_TOOL_HINTS)
            and ("crontab" in b_low or "cron " in b_low)
        )
        if not is_cron_tool and not is_shell_crontab:
            continue

        if is_shell_crontab:
            used_shell_crontab = True

        has_10am_beijing = (
            ("0 10 " in b_low and ("shanghai" in b_low or "cst" in b_low or "utc+8" in b_low or "beijing" in b_low or "北京" in b))
            or _re.search(r"0 2 \* \* [*0-9,-]+", b_low) is not None
            or "10:00" in b_low
            or "10am" in b_low
            or "10 am" in b_low
            or "早上 10" in b
            or "早上10" in b
            or "10 点" in b
            or "10点" in b
            or ("0 10 * * *" in b_low)
        )
        if has_10am_beijing:
            schedule_ok = True

        b_nospace = b_low.replace(" ", "")
        has_console = (
            ("channel" in b_low and "console" in b_low)
            or '"deliver":"console"' in b_nospace
            or '"deliver":"console:' in b_nospace
            or "deliver: console" in b_low
            or '"deliver":"origin"' in b_nospace
            or "deliver: origin" in b_low
        )
        if has_console:
            console_ok = True

    if used_shell_crontab:
        console_ok = True

    scores["cron_schedule_correct"] = 1.0 if schedule_ok else 0.0
    scores["prompt_mentions_astock"] = 1.0 if astock_ok else 0.0
    scores["delivery_console"] = 1.0 if console_ok else 0.0

    return scores
```

## LLM Judge Rubric

### task_completion (Weight: 50%)
- 1.0: A scheduled task fires at daily Beijing 10:00 (or weekdays
  only — smart interpretation), its prompt/script queries A-share
  index data and generates a briefing, and the output is routed to
  console.  Final reply confirms the setup.
- 0.75: Schedule is created with correct time but one minor gap
  (e.g. timezone not explicitly set but likely correct, or delivery
  channel not explicitly "console" but implied).
- 0.5: Some cron attempt was made but the time is wrong or the
  prompt doesn't mention A-shares.
- 0.25: Agent tried but the schedule was never actually created.
- 0.0: No scheduling attempt.

### tool_skill_use (Weight: 30%)
- 1.0: Clean, efficient use of cron / scheduling tools.  For shell-
  based approaches: the crontab expression is correct and a working
  script/command is referenced.
- 0.75: Mostly appropriate with one wasted call.
- 0.5: Multiple wasted calls or environment-diagnostic loops.
- 0.25: Tool use mostly unproductive.
- 0.0: No meaningful tool interaction.

### output_quality (Weight: 20%)
- 1.0: Final reply is in Chinese, clearly states the schedule
  (北京时间 10:00), the purpose (A 股指数简报), and delivery
  (控制台).
- 0.75: Clear but misses one detail.
- 0.5: Understandable but partially wrong.
- 0.25: Confusing.
- 0.0: No usable response.

Pass threshold: `total >= 0.6`.
