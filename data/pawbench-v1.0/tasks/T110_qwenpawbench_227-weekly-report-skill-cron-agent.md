---
id: 227-weekly-report-skill-cron-agent
name: Weekly Report Skill Cron Agent
category: guide-assistance
grading_type: hybrid
grading_weights:
  automated: 0.5
  llm_judge: 0.5
timeout_seconds: 900
input_modality: multimodal
external_dependency: none
origin_benchmark: pawbench
origin_task_id: 227-weekly-report-skill-cron-agent
complexity: L2
copaw:
  required_tools:
  - execute_shell_command
  - read_file
  required_skills:
  - cron
  distractor_skills: []
labels:
  scenario: Automation_Platform/Agent
  complexity: L2
  environment: closed
  modality:
    type: text
    channels: []
  capabilities:
  - Tool_Use
  - Planning
---

## Prompt

完成以下三项配置：1) 从 clawhub 搜索并安装一个 Github 相关的 skill；2) 创建一个每周五下午 5 点的定时任务，提醒我写周总结，channel 用 console，target-user 和 target-session 都用 default；3) 配置一个叫周报助手的 Agent，人格是细致的项目经理，擅长总结和汇报，使用默认模型。

## Expected Behavior

The user requested **three independent sub-tasks**.  A correct run
must finish **all three**, and each one is independently verifiable
from the transcript alone.  Different agent frameworks will use
different tools to achieve the same effect — that is fine, as long as
the *intent* is encoded in the tool call arguments.

### Sub-task 1 · Search & install a GitHub-related skill

The agent must do **one** of the following:

- (a) **Real install attempt:** invoke a skill-search/install style
  tool whose arguments mention GitHub (`github`, `gh`, `git`, `pr`,
  `pull request`, `repo`).
- (b) **Stub install:** if no such skill exists in the registry,
  create a placeholder skill on disk (`SKILL.md` or equivalent
  manifest) under a directory whose name encodes the same idea
  (e.g. `github-skill/`, `gh-skill/`).
- (c) **Explicit not-found report:** if the agent decides no suitable
  skill exists, the **final assistant reply** must explicitly tell
  the user that no GitHub skill was found, and list at least one
  search/keyword that was actually tried.

Silent skipping does not count.

### Sub-task 2 · Friday-5pm weekly-report cron job

A cron / scheduled-task tool call must be present whose arguments
encode **all** of:

- **schedule** = every Friday at 17:00 (5pm).  Acceptable forms:
  `Fri 17:00`, `friday 5pm`, `5pm on fri`, `0 17 * * 5`,
  `0 17 * * fri`, `每周五 17:00`, `每周五下午 5 点`.
- **channel** / **deliver** = `console`.
- **target-user** / `user` = `default`.
- **target-session** / `session` = `default`.
- **prompt / message** mentioning weekly report (`周报`, `周总结`,
  `weekly`, `weekly report`, `weekly summary`).

Missing any of `channel`, `target-user`, or `target-session` (the
three values the user *explicitly* spelled out) means the sub-task is
**not** complete.

### Sub-task 3 · Agent "周报助手"

There must be persistent evidence — either a write/edit/memory tool
call OR a `personality` / agent-config tool call — whose arguments
encode **both**:

- the agent name `周报助手` (acceptable transliterations: `weekly
  report assistant`, `weekly-report-assistant`);
- a personality directive that mentions a careful project manager who
  is good at summarising / reporting (`项目经理`, `project manager`,
  `总结`, `汇报`, `summary`, `report`).

The agent must use the **default model** — i.e. should not pass an
explicit `model=...` overriding the platform default.

### Final reply

The agent must produce a final assistant message in Chinese that
summarises which of the three sub-tasks succeeded and which (if any)
were skipped or had to be approximated.

## Grading Criteria

- [ ] Sub-task 1: GitHub-related skill installed, stubbed, **or** explicitly reported as missing in the final reply.
- [ ] Sub-task 2: cron tool call carries `Fri 17:00` semantics + `channel=console` + `target-user=default` + `target-session=default` + a "周报/weekly" prompt.
- [ ] Sub-task 3: persistent config / write tool call encodes `周报助手` + project-manager / summary-reporting personality, using the default model.
- [ ] Final assistant reply summarises the three sub-tasks in Chinese.

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """Sub-task aware grader for the 周报助手 weekly-report task."""
    import json as _json
    import re as _re

    def iter_messages(events, role):
        for e in events or []:
            if not isinstance(e, dict) or e.get("type") != "message":
                continue
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
        return text

    calls = list(iter_tool_calls(transcript))
    blobs = [args_blob(c) for c in calls]
    final = final_text(transcript)

    scores = {}
    scores["agent_responded"] = 1.0 if final.strip() else 0.0

    GH_TOKENS = ("github", "gh ", " gh", "pull request", "pull-request", " pr ", "repo", "git ")
    skill_done = False
    for c, b in zip(calls, blobs):
        name_low = (c.get("name") or "").lower()
        b_low = b.lower()
        looks_like_skill_op = any(
            hint in name_low
            for hint in ("skill", "install", "search", "write", "edit", "create_file", "patch")
        ) or "install" in b_low or "search" in b_low
        if not looks_like_skill_op:
            continue
        if any(t in b_low for t in GH_TOKENS):
            skill_done = True
            break
    if not skill_done:
        final_low = final.lower()
        mentions_gh = any(t in final_low for t in GH_TOKENS) or "github" in final_low
        not_found_phrases = (
            "未找到", "没找到", "找不到", "不存在",
            "no such skill", "not found", "doesn't exist", "does not exist",
            "no matching", "no suitable",
        )
        if mentions_gh and any(p in final_low for p in not_found_phrases):
            skill_done = True
    scores["subtask_skill_install"] = 1.0 if skill_done else 0.0

    cron_done = False
    for c, b in zip(calls, blobs):
        name_low = (c.get("name") or "").lower()
        b_low = b.lower()
        looks_like_cron = ("cron" in name_low or "schedule" in name_low or "cron" in b_low or "schedule" in b_low)
        if not looks_like_cron:
            continue

        has_friday = (
            "fri" in b_low
            or "friday" in b_low
            or "周五" in b
            or "* * 5" in b_low
            or "* * fri" in b_low
        )
        has_5pm = (
            "17:00" in b_low
            or "17 " in b_low
            or " 17:" in b_low
            or "0 17" in b_low
            or "5pm" in b_low
            or "5 pm" in b_low
            or "下午 5" in b
            or "下午5" in b
            or "17 点" in b
            or "17点" in b
        )
        b_nospace = b_low.replace(" ", "")
        has_channel_console = (
            ("channel" in b_low and "console" in b_low)
            or '"deliver":"console"' in b_nospace
            or "deliver: console" in b_low
            or '"deliver":"console:' in b_nospace
        )
        has_target_user = (
            ("target-user" in b_low and "default" in b_low)
            or ("target_user" in b_low and "default" in b_low)
            or ('"user":"default"' in b_nospace)
            or ('"to":"default"' in b_nospace)
            or ('"deliver":"console:default:' in b_nospace)
        )
        has_target_session = (
            ("target-session" in b_low and "default" in b_low)
            or ("target_session" in b_low and "default" in b_low)
            or ('"session":"default"' in b_nospace)
            or ('"sessiontarget":"default"' in b_nospace)
            or (':default:default"' in b_nospace)
        )
        has_weekly = (
            ("周报" in b) or ("周总结" in b)
            or ("weekly" in b_low) or ("weekly report" in b_low) or ("weekly summary" in b_low)
        )

        if has_friday and has_5pm and has_channel_console and has_target_user and has_target_session and has_weekly:
            cron_done = True
            break
    scores["subtask_cron_correct_params"] = 1.0 if cron_done else 0.0

    NAME_TOKENS = ("周报助手", "weekly report assistant", "weekly-report-assistant", "weekly_report_assistant")
    PERSONA_TOKENS = ("项目经理", "project manager", "总结", "汇报", "summary", "report")
    agent_done = False
    for c, b in zip(calls, blobs):
        name_low = (c.get("name") or "").lower()
        b_low = b.lower()
        looks_like_persist_or_config = any(
            hint in name_low
            for hint in (
                "edit", "write", "create_file", "patch",
                "memory", "remember", "save",
                "personality", "agent", "config", "profile",
            )
        )
        if not looks_like_persist_or_config:
            continue
        has_name = any(tok.lower() in b_low for tok in NAME_TOKENS) or any(tok in b for tok in NAME_TOKENS)
        has_persona = any(tok.lower() in b_low for tok in PERSONA_TOKENS) or any(tok in b for tok in PERSONA_TOKENS)
        if has_name and has_persona:
            agent_done = True
            break
    scores["subtask_personality_configured"] = 1.0 if agent_done else 0.0

    return scores
```

## LLM Judge Rubric

### task_completion (Weight: 50%)
Count how many of the **three sub-tasks** are genuinely complete.

- 1.0: All three sub-tasks complete (GitHub skill
  installed/stubbed/honestly reported; cron uses Fri-17:00 +
  channel=console + target-user=default + target-session=default with
  a 周报/weekly prompt; 周报助手 agent has a persisted
  project-manager personality on the default model), AND the final
  reply summarises the three.
- 0.75: Three sub-tasks attempted with one minor parameter omission
  (e.g. cron has Fri-17:00/console/weekly-prompt but omits one of
  target-user/target-session, or 周报助手 personality is recorded but
  doesn't mention the project-manager / summary angle).
- 0.5: Exactly one sub-task fully complete and the other two are
  partially attempted; or two sub-tasks complete and one is silently
  dropped.
- 0.25: Only one sub-task complete; the other two are missing or
  abandoned without any user-facing explanation.
- 0.0: None of the three sub-tasks complete; or no final user-facing
  reply at all.

### tool_skill_use (Weight: 30%)
- 1.0: All tool calls are appropriate; arguments faithfully encode the
  user's explicit parameters (Fri-17:00 / channel=console /
  target-user=default / target-session=default / 周报 prompt for
  cron, 周报助手 + project-manager persona, GitHub keyword for the
  skill search); no runaway loops.
- 0.75: Mostly appropriate with one wrong call or one missing
  user-supplied parameter.
- 0.5: Multiple wrong/wasted calls, or important user-supplied
  parameters silently dropped.
- 0.25: Tool use mostly unproductive.
- 0.0: No meaningful tool interaction.

### output_quality (Weight: 20%)
- 1.0: Final reply is in Chinese, well-structured (clear per-sub-task
  status), and faithfully reports what was actually done — including
  any sub-task that could not be completed and why.
- 0.75: Clear and accurate but glosses over one sub-task.
- 0.5: Understandable but partially in the wrong language, or
  misrepresents what actually happened.
- 0.25: Confusing or contradicts the transcript.
- 0.0: No usable final response.

Pass threshold: `total >= 0.6`.
