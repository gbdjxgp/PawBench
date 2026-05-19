---
id: 234-doc-butler-skill-cron-agent
name: Doc Butler Skill Cron Agent
category: guide-assistance
grading_type: hybrid
grading_weights:
  automated: 0.5
  llm_judge: 0.5
timeout_seconds: 900
input_modality: multimodal
external_dependency: none
origin_benchmark: pawbench
origin_task_id: 234-doc-butler-skill-cron-agent
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

完成以下三项配置：1) 从 clawhub 搜索并安装一个 Markdown 编辑相关的 skill；2) 创建一个每周三下午 3 点的定时任务提醒我更新项目文档，channel 用 console，target-user 和 target-session 都用 default；3) 创建一个叫文档管家的 Agent，人格是对文档格式和内容质量极其挑剔的技术写作专家，使用默认模型。

## Expected Behavior

The user requested **three independent sub-tasks**.  A correct run
must finish **all three**, and each one is independently verifiable
from the transcript alone.  Different agent frameworks will use
different tools to achieve the same effect — that is fine, as long as
the *intent* is encoded in the tool call arguments.

### Sub-task 1 · Search & install a Markdown-editing skill

The agent must do **one** of the following:

- (a) **Real install attempt:** invoke a skill-search/install style
  tool whose arguments mention Markdown editing (`markdown`, `md`,
  `md editor`, `markdown editor`, `mdx`).
- (b) **Stub install:** if no such skill exists in the registry,
  create a placeholder skill on disk (`SKILL.md` or equivalent
  manifest) under a directory whose name encodes the same idea
  (e.g. `markdown-editor/`, `md-skill/`).
- (c) **Explicit not-found report:** if the agent decides no suitable
  skill exists, the **final assistant reply** must explicitly tell
  the user that no Markdown-editing skill was found, and list at
  least one search/keyword that was actually tried.

Silent skipping does not count.

### Sub-task 2 · Wednesday-3pm doc-reminder cron job

A cron / scheduled-task tool call must be present whose arguments
encode **all** of:

- **schedule** = every Wednesday at 15:00 (3pm).  Acceptable forms:
  `Wed 15:00`, `wednesday 3pm`, `0 15 * * 3`, `0 15 * * wed`,
  `每周三 15:00`, `每周三下午 3 点`.
- **channel** / **deliver** = `console`.
- **target-user** / `user` = `default`.
- **target-session** / `session` = `default`.
- **prompt / message** mentioning project-doc update (`项目文档`,
  `更新文档`, `doc`, `docs`, `documentation`, `update doc`).

Missing any of `channel`, `target-user`, or `target-session` (the
three values the user *explicitly* spelled out) means the sub-task is
**not** complete.

### Sub-task 3 · Agent "文档管家"

There must be persistent evidence — either a write/edit/memory tool
call OR a `personality` / agent-config tool call — whose arguments
encode **both**:

- the agent name `文档管家` (acceptable transliterations: `doc
  butler`, `document butler`, `doc-butler`);
- a personality directive that mentions a picky / strict technical
  writer who cares about doc format and content quality (`技术写作`
  / `technical writer` / `技术文档` / `挑剔` / `strict` / `picky` /
  plus a quality-related word such as `格式` / `format` / `内容质量`
  / `content quality`).

The agent must use the **default model** — i.e. should not pass an
explicit `model=...` overriding the platform default.

### Final reply

The agent must produce a final assistant message in Chinese that
summarises which of the three sub-tasks succeeded and which (if any)
were skipped or had to be approximated.

## Grading Criteria

- [ ] Sub-task 1: Markdown-editing skill installed, stubbed, **or** explicitly reported as missing in the final reply.
- [ ] Sub-task 2: cron tool call carries `Wed 15:00` semantics + `channel=console` + `target-user=default` + `target-session=default` + a "项目文档/doc" prompt.
- [ ] Sub-task 3: persistent config / write tool call encodes `文档管家` + picky technical-writer personality, using the default model.
- [ ] Final assistant reply summarises the three sub-tasks in Chinese.

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """Sub-task aware grader for the 文档管家 weekly-doc-reminder task."""
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

    MD_TOKENS = ("markdown", "md editor", "markdown editor", "mdx", " md ", ".md")
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
        if any(t in b_low for t in MD_TOKENS):
            skill_done = True
            break
    if not skill_done:
        final_low = final.lower()
        mentions_md = any(t in final_low for t in MD_TOKENS)
        not_found_phrases = (
            "未找到", "没找到", "找不到", "不存在",
            "no such skill", "not found", "doesn't exist", "does not exist",
            "no matching", "no suitable",
        )
        if mentions_md and any(p in final_low for p in not_found_phrases):
            skill_done = True
    scores["subtask_skill_install"] = 1.0 if skill_done else 0.0

    cron_done = False
    for c, b in zip(calls, blobs):
        name_low = (c.get("name") or "").lower()
        b_low = b.lower()
        looks_like_cron = ("cron" in name_low or "schedule" in name_low or "cron" in b_low or "schedule" in b_low)
        if not looks_like_cron:
            continue

        has_wed = (
            "wed" in b_low
            or "wednesday" in b_low
            or "周三" in b
            or "* * 3" in b_low
        )
        has_3pm = (
            "15:00" in b_low
            or " 15 " in b_low
            or " 15:" in b_low
            or "0 15" in b_low
            or "3pm" in b_low
            or "3 pm" in b_low
            or "下午 3" in b
            or "下午3" in b
            or "15 点" in b
            or "15点" in b
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
        has_doc = (
            ("项目文档" in b) or ("更新文档" in b) or ("文档" in b)
            or ("doc" in b_low) or ("docs" in b_low) or ("documentation" in b_low) or ("update doc" in b_low)
        )

        if has_wed and has_3pm and has_channel_console and has_target_user and has_target_session and has_doc:
            cron_done = True
            break
    scores["subtask_cron_correct_params"] = 1.0 if cron_done else 0.0

    NAME_TOKENS = ("文档管家", "doc butler", "document butler", "doc-butler", "doc_butler")
    PERSONA_TOKENS_ROLE = ("技术写作", "技术文档", "technical writer", "technical writing")
    PERSONA_TOKENS_QUALITY = ("挑剔", "严苛", "strict", "picky", "格式", "format", "内容质量", "content quality", "quality")
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
        has_role = any(tok.lower() in b_low for tok in PERSONA_TOKENS_ROLE) or any(tok in b for tok in PERSONA_TOKENS_ROLE)
        has_quality = any(tok.lower() in b_low for tok in PERSONA_TOKENS_QUALITY) or any(tok in b for tok in PERSONA_TOKENS_QUALITY)
        if has_name and has_role and has_quality:
            agent_done = True
            break
    scores["subtask_personality_configured"] = 1.0 if agent_done else 0.0

    return scores
```

## LLM Judge Rubric

### task_completion (Weight: 50%)
Count how many of the **three sub-tasks** are genuinely complete.

- 1.0: All three sub-tasks complete (Markdown-editing skill
  installed/stubbed/honestly reported; cron uses Wed-15:00 +
  channel=console + target-user=default + target-session=default with
  a 项目文档/doc prompt; 文档管家 agent has a persisted picky
  technical-writer personality on the default model), AND the final
  reply summarises the three.
- 0.75: Three sub-tasks attempted with one minor parameter omission
  (e.g. cron has Wed-15:00/console/doc-prompt but omits one of
  target-user/target-session, or 文档管家 personality is recorded
  but doesn't restate the picky / format / content-quality angle).
- 0.5: Exactly one sub-task fully complete and the other two are
  partially attempted; or two sub-tasks complete and one is silently
  dropped.
- 0.25: Only one sub-task complete; the other two are missing or
  abandoned without any user-facing explanation.
- 0.0: None of the three sub-tasks complete; or no final user-facing
  reply at all.

### tool_skill_use (Weight: 30%)
- 1.0: All tool calls are appropriate; arguments faithfully encode the
  user's explicit parameters (Wed-15:00 / channel=console /
  target-user=default / target-session=default / 项目文档 prompt for
  cron, 文档管家 + picky technical-writer persona, Markdown keyword
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
