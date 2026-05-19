---
id: 230-study-buddy-skill-cron-agent
name: Study Buddy Skill Cron Agent
category: guide-assistance
grading_type: hybrid
grading_weights:
  automated: 0.5
  llm_judge: 0.5
timeout_seconds: 600
input_modality: multimodal
external_dependency: none
origin_benchmark: pawbench
origin_task_id: 230-study-buddy-skill-cron-agent
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

完成以下三项配置：1) 安装 Home Music skill；2) 创建一个每隔 4 小时的定时任务提醒我休息一下，channel 用 console，target-user 和 target-session 都用 default；3) 配置一个叫学习伙伴的 Agent，人格设置里他需要一到休息时间就建议我放松，使用默认模型。

## Expected Behavior

The user requested **three independent sub-tasks**.  A correct run must
finish **all three**, and each one is independently verifiable from the
transcript alone.  Different agent frameworks will use different tools
to achieve the same effect — that is fine, as long as the *intent* is
encoded in the tool call arguments.

### Sub-task 1 · Install "Home Music" skill

The agent must do **one** of the following:

- (a) **Real install attempt:** invoke a skill-install style tool whose
  arguments mention "home" + "music" (e.g. `hermes skills install
  home-music`, `skills_install`, or any equivalent wrapper).  A single
  successful or unsuccessful install attempt is acceptable.
- (b) **Stub install:** if no such skill exists in the registry, the
  agent may create a placeholder skill on disk — write a `SKILL.md`
  (or equivalent manifest) under a `home-music/` directory inside the
  workspace's skills location.
- (c) **Explicit not-found report:** if the agent decides the skill
  genuinely does not exist and cannot be stubbed, the **final
  assistant reply** must explicitly tell the user that "Home Music"
  was not found, and list at least one alternative searched (so the
  user knows it was actually attempted).

Silent skipping ("我先做后面两个") **does not** count as completing
sub-task 1.

### Sub-task 2 · 4-hour break-reminder cron job

A cron / scheduled-task tool call must be present whose arguments
encode **all** of:

- **schedule** = every 4 hours.  Any of these forms is acceptable:
  `every 4 hours`, `every 4h`, `4h`, `0 */4 * * *`, `*/4 * * *`,
  `每 4 小时`, `每隔 4 小时`.
- **channel** / **deliver** = `console`.
- **target-user** / `user` = `default`.
- **target-session** / `session` = `default`.
- **prompt / message** containing 休息 / break / rest 类语义。

Missing any of `channel`, `target-user`, or `target-session` (the
three values the user *explicitly* spelled out) means the sub-task is
**not** complete.

### Sub-task 3 · Agent "学习伙伴"

There must be persistent evidence — either a write/edit/memory tool
call OR a `personality` / agent-config tool call — whose arguments
encode **both**:

- the agent name `学习伙伴` (or `study buddy` / `study partner` are
  acceptable transliterations);
- a personality directive that mentions the break-time-relax behaviour
  (休息 + 放松 / break + relax 类组合).

The agent must use the **default model** — i.e. should not pass an
explicit `model=...` overriding the platform default.

### Final reply

The agent must produce a final assistant message in Chinese that
summarises which of the three sub-tasks succeeded and which (if any)
were skipped or had to be approximated.  Stalling in tool calls
without a final user-facing summary is **not** acceptable.

## Grading Criteria

- [ ] Sub-task 1: Home Music skill installed, stubbed, **or** explicitly reported as missing in the final reply.
- [ ] Sub-task 2: cron tool call carries `every 4 hours` semantics + `channel=console` + `target-user=default` + `target-session=default` + a "休息/break" prompt.
- [ ] Sub-task 3: persistent config / write tool call encodes `学习伙伴` agent name + personality with break-time-relax behaviour, using the default model.
- [ ] Final assistant reply summarises the three sub-tasks in Chinese.

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """Sub-task aware grader for the "Home Music + cron + 学习伙伴" task.

    Strategy:

    * Read the transcript only — different agent frameworks (copaw,
      openclaw, hermes) write to different filesystem paths, so we
      avoid agent-specific path checks.
    * For each of the 3 sub-tasks, look at *all* assistant tool calls
      and the final assistant text, and decide whether the *intent*
      was encoded somewhere observable.
    * Treat "explicitly reported as missing in the final reply" as a
      legitimate completion of sub-task 1 (Home Music skill genuinely
      may not exist in the registry; what matters is that the agent
      did not silently drop it).
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
    fulltext = "\n".join(blobs) + "\n" + final_text(transcript)
    fulltext_low = fulltext.lower()

    scores = {}

    final = final_text(transcript)
    scores["agent_responded"] = 1.0 if final.strip() else 0.0

    skill_install_done = False
    for c, b in zip(calls, blobs):
        name_low = (c.get("name") or "").lower()
        b_low = b.lower()
        mentions_home_music = ("home" in b_low and "music" in b_low) or "home-music" in b_low or "home_music" in b_low
        if not mentions_home_music:
            continue
        if any(hint in name_low for hint in ("skill", "install", "write", "edit", "create_file", "patch")):
            skill_install_done = True
            break
        if "install" in b_low:
            skill_install_done = True
            break
    if not skill_install_done:
        final_low = final.lower()
        mentions_home_music_in_final = (
            ("home" in final_low and "music" in final_low) or "home music" in final_low
        )
        not_found_phrases = (
            "未找到", "没找到", "找不到", "不存在",
            "no such skill", "not found", "doesn't exist", "does not exist",
            "no matching",
        )
        if mentions_home_music_in_final and any(p in final_low for p in not_found_phrases):
            skill_install_done = True
    scores["subtask_skill_install"] = 1.0 if skill_install_done else 0.0

    cron_done = False
    for c, b in zip(calls, blobs):
        name_low = (c.get("name") or "").lower()
        b_low = b.lower()
        looks_like_cron = ("cron" in name_low or "schedule" in name_low or "cron" in b_low or "schedule" in b_low)
        if not looks_like_cron:
            continue

        has_4h = (
            _re.search(r"\b4\s*h(our)?s?\b", b_low) is not None
            or "*/4" in b_low
            or "0 */4" in b_low
            or "every 4" in b_low
            or "每 4" in b
            or "每4" in b
            or "每隔 4" in b
            or "每隔4" in b
            or "4 小时" in b
            or "4小时" in b
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
        has_break = ("休息" in b) or ("break" in b_low) or ("rest" in b_low)

        if has_4h and has_channel_console and has_target_user and has_target_session and has_break:
            cron_done = True
            break
    scores["subtask_cron_correct_params"] = 1.0 if cron_done else 0.0

    agent_done = False
    NAME_TOKENS = ("学习伙伴", "study buddy", "study partner", "study-buddy", "study-partner")
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
        has_name = any(tok in b_low for tok in (t.lower() for t in NAME_TOKENS))
        has_break_relax = (
            ("休息" in b and ("放松" in b or "relax" in b_low))
            or ("break" in b_low and ("relax" in b_low or "放松" in b))
        )
        if has_name and has_break_relax:
            agent_done = True
            break
    scores["subtask_personality_configured"] = 1.0 if agent_done else 0.0

    return scores
```

## LLM Judge Rubric

### task_completion (Weight: 50%)
Count how many of the **three sub-tasks** are genuinely complete.

- 1.0: All three sub-tasks complete per the criteria above (Home Music
  installed/stubbed/honestly reported, cron uses every-4-hours +
  channel=console + target-user=default + target-session=default with a
  break prompt, 学习伙伴 agent has a persisted personality on the
  default model), AND the final reply summarises the three.
- 0.75: Three sub-tasks attempted with one minor parameter omission
  (e.g. cron uses every-4-hours/console/break-prompt but omits one of
  target-user/target-session, or 学习伙伴 personality is recorded but
  doesn't restate the relax-on-break behaviour).
- 0.5: Exactly one sub-task fully complete and the other two are
  partially attempted; or two sub-tasks complete and one is silently
  dropped.
- 0.25: Only one sub-task complete; the other two are missing or
  abandoned without any user-facing explanation.
- 0.0: None of the three sub-tasks complete; or no final user-facing
  reply at all.

### tool_skill_use (Weight: 30%)
- 1.0: All tool calls are appropriate; arguments faithfully encode the
  user's explicit parameters (channel/target-user/target-session for
  cron, agent name + personality for 学习伙伴, install attempt for
  Home Music); no runaway loops.
- 0.75: Mostly appropriate with one wrong call or one missing
  user-supplied parameter.
- 0.5: Multiple wrong/wasted calls, or important user-supplied
  parameters are silently dropped.
- 0.25: Tool use mostly unproductive or several user-supplied
  parameters dropped.
- 0.0: No meaningful tool interaction.

### output_quality (Weight: 20%)
- 1.0: Final reply is in Chinese, well-structured (clear per-sub-task
  status), and faithfully reports what was actually done — including
  any sub-task that could not be completed and why.
- 0.75: Clear and accurate but glosses over one sub-task.
- 0.5: Understandable but partially in the wrong language, or
  misrepresents what actually happened (claims success for a sub-task
  that was not actually executed).
- 0.25: Confusing or contradicts the transcript.
- 0.0: No usable final response.

Pass threshold: `total >= 0.6`.
