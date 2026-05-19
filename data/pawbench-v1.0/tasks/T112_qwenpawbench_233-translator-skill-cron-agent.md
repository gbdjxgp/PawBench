---
id: 233-translator-skill-cron-agent
name: Translator Skill Cron Agent
category: guide-assistance
grading_type: hybrid
grading_weights:
  automated: 0.5
  llm_judge: 0.5
timeout_seconds: 900
input_modality: multimodal
external_dependency: none
origin_benchmark: pawbench
origin_task_id: 233-translator-skill-cron-agent
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

完成以下三项配置：1) 从 clawhub 搜索并安装一个翻译相关的 skill；2) 设定每天下午 6 点的定时任务提醒我学英语，channel 用 console，target-user 和 target-session 都用 default；3) 创建一个叫翻译官的 Agent，人格设定为精通中英日三语的专业翻译，风格严谨且地道，使用默认模型。

## Expected Behavior

The user requested **three independent sub-tasks**.  A correct run
must finish **all three**, and each one is independently verifiable
from the transcript alone.  Different agent frameworks will use
different tools to achieve the same effect — that is fine, as long as
the *intent* is encoded in the tool call arguments.

### Sub-task 1 · Search & install a translation skill

The agent must do **one** of the following:

- (a) **Real install attempt:** invoke a skill-search/install style
  tool whose arguments mention translation (`translate`,
  `translator`, `translation`, `i18n`, `翻译`).
- (b) **Stub install:** if no such skill exists in the registry,
  create a placeholder skill on disk (`SKILL.md` or equivalent
  manifest) under a directory whose name encodes the same idea
  (e.g. `translator/`, `translate-skill/`).
- (c) **Explicit not-found report:** if the agent decides no suitable
  skill exists, the **final assistant reply** must explicitly tell
  the user that no translation skill was found, and list at least
  one search/keyword that was actually tried.

Silent skipping does not count.

### Sub-task 2 · Daily-6pm English-study cron job

A cron / scheduled-task tool call must be present whose arguments
encode **all** of:

- **schedule** = every day at 18:00 (6pm).  Acceptable forms:
  `daily 18:00`, `every day 6pm`, `0 18 * * *`, `每天 18:00`,
  `每天下午 6 点`.
- **channel** / **deliver** = `console`.
- **target-user** / `user` = `default`.
- **target-session** / `session` = `default`.
- **prompt / message** mentioning English study (`英语`, `学英语`,
  `english`, `study english`, `learn english`).

Missing any of `channel`, `target-user`, or `target-session` (the
three values the user *explicitly* spelled out) means the sub-task is
**not** complete.

### Sub-task 3 · Agent "翻译官"

There must be persistent evidence — either a write/edit/memory tool
call OR a `personality` / agent-config tool call — whose arguments
encode **both**:

- the agent name `翻译官` (acceptable transliterations: `translator`,
  `the translator`);
- a personality directive that mentions multilingual translation
  expertise — at least two of `中` / `英` / `日` (or `Chinese` /
  `English` / `Japanese`) plus a reference to professional /
  rigorous / idiomatic translation (`专业` / `严谨` / `地道` /
  `professional` / `rigorous` / `idiomatic` / `translation`).

The agent must use the **default model** — i.e. should not pass an
explicit `model=...` overriding the platform default.

### Final reply

The agent must produce a final assistant message in Chinese that
summarises which of the three sub-tasks succeeded and which (if any)
were skipped or had to be approximated.

## Grading Criteria

- [ ] Sub-task 1: translation skill installed, stubbed, **or** explicitly reported as missing in the final reply.
- [ ] Sub-task 2: cron tool call carries `daily 18:00` semantics + `channel=console` + `target-user=default` + `target-session=default` + an "英语/english" prompt.
- [ ] Sub-task 3: persistent config / write tool call encodes `翻译官` + multilingual professional-translator personality, using the default model.
- [ ] Final assistant reply summarises the three sub-tasks in Chinese.

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """Sub-task aware grader for the 翻译官 daily-6pm task."""
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

    TR_TOKENS = ("translate", "translator", "translation", "i18n", "翻译")
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
        if any(t.lower() in b_low for t in TR_TOKENS) or "翻译" in b:
            skill_done = True
            break
    if not skill_done:
        final_low = final.lower()
        mentions_tr = any(t.lower() in final_low for t in TR_TOKENS) or "翻译" in final
        not_found_phrases = (
            "未找到", "没找到", "找不到", "不存在",
            "no such skill", "not found", "doesn't exist", "does not exist",
            "no matching", "no suitable",
        )
        if mentions_tr and any(p in final_low for p in not_found_phrases):
            skill_done = True
    scores["subtask_skill_install"] = 1.0 if skill_done else 0.0

    cron_done = False
    for c, b in zip(calls, blobs):
        name_low = (c.get("name") or "").lower()
        b_low = b.lower()
        looks_like_cron = ("cron" in name_low or "schedule" in name_low or "cron" in b_low or "schedule" in b_low)
        if not looks_like_cron:
            continue

        has_daily = (
            "daily" in b_low
            or "every day" in b_low
            or "每天" in b
            or _re.search(r"\*\s*\*\s*\*", b_low) is not None
        )
        has_6pm = (
            "18:00" in b_low
            or " 18 " in b_low
            or " 18:" in b_low
            or "0 18" in b_low
            or "6pm" in b_low
            or "6 pm" in b_low
            or "下午 6" in b
            or "下午6" in b
            or "18 点" in b
            or "18点" in b
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
        has_english = (
            ("英语" in b) or ("学英语" in b)
            or ("english" in b_low) or ("study english" in b_low) or ("learn english" in b_low)
        )

        if has_daily and has_6pm and has_channel_console and has_target_user and has_target_session and has_english:
            cron_done = True
            break
    scores["subtask_cron_correct_params"] = 1.0 if cron_done else 0.0

    NAME_TOKENS = ("翻译官", "translator", "the translator")
    LANG_TOKENS_CN = ("中", "英", "日")
    LANG_TOKENS_EN = ("chinese", "english", "japanese")
    QUALITY_TOKENS = ("专业", "严谨", "地道", "professional", "rigorous", "idiomatic", "translation")
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
        has_name = any(tok.lower() in b_low for tok in NAME_TOKENS) or "翻译官" in b
        lang_hits_cn = sum(1 for tok in LANG_TOKENS_CN if tok in b)
        lang_hits_en = sum(1 for tok in LANG_TOKENS_EN if tok in b_low)
        has_two_languages = (lang_hits_cn >= 2) or (lang_hits_en >= 2) or (lang_hits_cn + lang_hits_en >= 2)
        has_quality = any(tok.lower() in b_low for tok in QUALITY_TOKENS) or any(tok in b for tok in QUALITY_TOKENS)
        if has_name and has_two_languages and has_quality:
            agent_done = True
            break
    scores["subtask_personality_configured"] = 1.0 if agent_done else 0.0

    return scores
```

## LLM Judge Rubric

### task_completion (Weight: 50%)
Count how many of the **three sub-tasks** are genuinely complete.

- 1.0: All three sub-tasks complete (translation skill
  installed/stubbed/honestly reported; cron uses daily-18:00 +
  channel=console + target-user=default + target-session=default with
  an 英语/english prompt; 翻译官 agent has a persisted multilingual
  professional-translator personality on the default model), AND the
  final reply summarises the three.
- 0.75: Three sub-tasks attempted with one minor parameter omission
  (e.g. cron has daily-18:00/console/english-prompt but omits one of
  target-user/target-session, or 翻译官 personality is recorded but
  doesn't restate the multilingual / 严谨 / 地道 angle).
- 0.5: Exactly one sub-task fully complete and the other two are
  partially attempted; or two sub-tasks complete and one is silently
  dropped.
- 0.25: Only one sub-task complete; the other two are missing or
  abandoned without any user-facing explanation.
- 0.0: None of the three sub-tasks complete; or no final user-facing
  reply at all.

### tool_skill_use (Weight: 30%)
- 1.0: All tool calls are appropriate; arguments faithfully encode the
  user's explicit parameters (daily-18:00 / channel=console /
  target-user=default / target-session=default / 英语 prompt for
  cron, 翻译官 + multilingual persona, translation keyword for the
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
