---
id: 225-multi-config-skill-cron-agent
name: Multi Config Skill Cron Agent
category: guid-assistance
grading_type: hybrid
grading_weights:
  automated: 0.5
  llm_judge: 0.5
timeout_seconds: 600
input_modality: multimodal
external_dependency: none
origin_benchmark: pawbench
origin_task_id: 225-multi-config-skill-cron-agent
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

完成以下三项配置：1) 从 clawhub 搜索并安装一个代码格式化相关的 skill；2) 设定每隔 3 小时的定时任务提醒我做代码提交，定时任务的 channel 用 console；3) 创建一个叫 GitMaster 的 Agent，人格是 Git 版本控制专家，使用默认模型。

## Expected Behavior

The user requested **three independent sub-tasks**.  A correct run
must finish **all three**, and each one is independently verifiable
from the transcript alone.  Different agent frameworks will use
different tools to achieve the same effect — that is fine, as long as
the *intent* is encoded in the tool call arguments.

### Sub-task 1 · Search & install a code-formatting skill

The agent must do **one** of the following:

- (a) **Real install attempt:** invoke a skill-search/install style
  tool whose arguments mention a code formatter — keywords such as
  `format`, `formatter`, `prettier`, `black`, `gofmt`, `lint`, `code
  style`, `代码格式化`, `格式化` qualify.
- (b) **Stub install:** if no such skill exists in the registry,
  create a placeholder skill on disk (`SKILL.md` or equivalent
  manifest) under a directory whose name encodes the same idea
  (e.g. `code-formatter/`, `prettier-skill/`).
- (c) **Explicit not-found report:** if the agent decides no suitable
  skill exists, the **final assistant reply** must explicitly tell
  the user that no code-formatting skill was found, and list at least
  one search/keyword that was actually tried.

Silent skipping does not count.

### Sub-task 2 · Every-3-hours commit-reminder cron job

A cron / scheduled-task tool call must be present whose arguments
encode **all** of:

- **schedule** = every 3 hours.  Acceptable forms: `every 3 hours`,
  `every 3h`, `3h`, `0 */3 * * *`, `*/3 * * *`, `每 3 小时`,
  `每隔 3 小时`.
- **channel** / **deliver** = `console`.
- **prompt / message** mentioning code commit (`commit`, `提交`,
  `代码提交`).

(`target-user` / `target-session` were not specified by the user this
time, so they are not required.)

### Sub-task 3 · Agent "GitMaster"

There must be persistent evidence — either a write/edit/memory tool
call OR a `personality` / agent-config tool call — whose arguments
encode **both**:

- the agent name `GitMaster` (case-insensitive; `git-master` /
  `git_master` are acceptable);
- a personality directive that mentions Git / version control
  expertise (`Git`, `version control`, `版本控制`).

The agent must use the **default model** — i.e. should not pass an
explicit `model=...` overriding the platform default.

### Final reply

The agent must produce a final assistant message in Chinese that
summarises which of the three sub-tasks succeeded and which (if any)
were skipped or had to be approximated.

## Grading Criteria

- [ ] Sub-task 1: code-formatting skill installed, stubbed, **or** explicitly reported as missing in the final reply.
- [ ] Sub-task 2: cron tool call carries `every 3 hours` semantics + `channel=console` + a "commit/提交" prompt.
- [ ] Sub-task 3: persistent config / write tool call encodes `GitMaster` + Git/version-control personality, using the default model.
- [ ] Final assistant reply summarises the three sub-tasks in Chinese.

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """Sub-task aware grader for the GitMaster multi-config task.

    Strategy: read the transcript only — different agent frameworks
    write to different filesystem paths, so we avoid agent-specific
    path checks.  For each of the 3 sub-tasks, look at all assistant
    tool calls and the final assistant text and decide whether the
    intent was encoded somewhere observable.
    """
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

    FORMAT_TOKENS = (
        "format", "formatter", "prettier", "black", "gofmt", "rustfmt",
        "lint", "linter", "code style", "代码格式", "格式化",
    )
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
        if any(t.lower() in b_low for t in FORMAT_TOKENS) or any(t in b for t in FORMAT_TOKENS):
            skill_done = True
            break
    if not skill_done:
        final_low = final.lower()
        mentions_format = any(t.lower() in final_low for t in FORMAT_TOKENS) or any(t in final for t in FORMAT_TOKENS)
        not_found_phrases = (
            "未找到", "没找到", "找不到", "不存在",
            "no such skill", "not found", "doesn't exist", "does not exist",
            "no matching", "no suitable",
        )
        if mentions_format and any(p in final_low for p in not_found_phrases):
            skill_done = True
    scores["subtask_skill_install"] = 1.0 if skill_done else 0.0

    cron_done = False
    for c, b in zip(calls, blobs):
        name_low = (c.get("name") or "").lower()
        b_low = b.lower()
        looks_like_cron = ("cron" in name_low or "schedule" in name_low or "cron" in b_low or "schedule" in b_low)
        if not looks_like_cron:
            continue

        has_3h = (
            _re.search(r"\b3\s*h(our)?s?\b", b_low) is not None
            or "*/3" in b_low
            or "0 */3" in b_low
            or "every 3" in b_low
            or "每 3" in b
            or "每3" in b
            or "每隔 3" in b
            or "每隔3" in b
            or "3 小时" in b
            or "3小时" in b
        )
        b_nospace = b_low.replace(" ", "")
        has_channel_console = (
            ("channel" in b_low and "console" in b_low)
            or '"deliver":"console"' in b_nospace
            or "deliver: console" in b_low
            or '"deliver":"console:' in b_nospace
        )
        has_commit = ("提交" in b) or ("代码提交" in b) or ("commit" in b_low)

        if has_3h and has_channel_console and has_commit:
            cron_done = True
            break
    scores["subtask_cron_correct_params"] = 1.0 if cron_done else 0.0

    NAME_TOKENS = ("gitmaster", "git-master", "git_master", "git master")
    PERSONA_TOKENS = ("git", "version control", "版本控制")
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
        has_name = any(tok in b_low for tok in NAME_TOKENS)
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

- 1.0: All three sub-tasks complete (code-format skill
  installed/stubbed/honestly reported; cron uses every-3-hours +
  channel=console + commit-reminder prompt; GitMaster agent has a
  persisted Git/version-control personality on the default model),
  AND the final reply summarises the three.
- 0.75: Three sub-tasks attempted with one minor parameter omission
  (e.g. cron has every-3-hours + console but the prompt is generic
  rather than mentioning commits, or GitMaster persona is recorded
  but doesn't restate the Git/version-control angle).
- 0.5: Exactly one sub-task fully complete and the other two are
  partially attempted; or two sub-tasks complete and one is silently
  dropped.
- 0.25: Only one sub-task complete; the other two are missing or
  abandoned without any user-facing explanation.
- 0.0: None of the three sub-tasks complete; or no final user-facing
  reply at all.

### tool_skill_use (Weight: 30%)
- 1.0: All tool calls are appropriate; arguments faithfully encode the
  user's explicit parameters (every-3-hours / channel=console / commit
  prompt for cron, GitMaster name + Git persona, code-format keyword
  for the skill search); no runaway loops.
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
