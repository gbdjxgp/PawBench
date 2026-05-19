---
id: 189-memory-step-by-step
name: Memory Step By Step
category: memory
grading_type: hybrid
grading_weights:
  automated: 0.5
  llm_judge: 0.5
timeout_seconds: 300
input_modality: text-only
external_dependency: none
origin_benchmark: pawbench
origin_task_id: 189-memory-step-by-step
complexity: L1
copaw:
  required_tools:
  - read_file
  - write_file
  - edit_file
  required_skills: []
  distractor_skills: []
labels:
  scenario: Automation_Platform/Agent
  complexity: L1
  environment: closed
  modality:
    type: text
  capabilities:
  - Tool_Use
---

## Prompt

以后回复复杂问题的时候分步骤说，别一股脑全堆一起

## Expected Behavior

The user is teaching the agent a long-term **answering style preference**:

> When future answers are complex, deliver them **step by step** instead
> of dumping everything in one block.

A correct run must satisfy **all** of the following:

- **Persist the preference.** The agent must invoke a persistence/memory
  tool call whose arguments encode this preference (mentioning at least
  one of: 分步 / 步骤 / step / step by step / 逐步 / 一步一步 / one
  step at a time, …).  Different agent frameworks expose this
  differently:
  - copaw / qwenpaw 通常 `write_file` / `edit` 一个 markdown 记忆文件
    （`PROFILE.md`、`MEMORY.md`、`USER.md`、`SOUL.md` …）；
  - openclaw 的 `edit` 工具可能把偏好追加到 `SOUL.md` / `USER.md`；
  - hermes 的 `memory` 工具会把条目写入它自身的 store。

  上述任意一种都视为合规。仅口头答复"好的我记住了"而**没有**任何
  持久化工具调用，**不**视为完成。

- **Acknowledge the preference in the reply.** The final assistant
  message must confirm in Chinese that the request has been understood
  / recorded, and the wording itself should reflect the preference
  (mention 分步 / 步骤 / step-by-step 等)。

- **No off-task actions.** Don't start unrelated tasks just because the
  agent expects to write *something* — the user only asked it to
  remember the preference.

It is *not* required that the preference be visible in any specific
file on the workspace filesystem — some agents persist memory inside an
internal store (SQLite, JSON in the agent's home directory, etc.) and
some write to a different markdown filename than others. **Evidence in
the transcript (a tool call with the right arguments + a Chinese
acknowledgement) is sufficient.**

## Grading Criteria

- [ ] Agent invoked a persistence/memory tool with arguments encoding the "answer step by step" preference.
- [ ] Final assistant reply confirms the preference in Chinese.
- [ ] No unrelated tool calls or off-task output.

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """Lenient, agent-neutral checks for the "answer step by step" memory task.

    Same design as task 003-output-preference:

    * Don't hard-code an agent-specific filesystem path.  copaw /
      openclaw / hermes each write the preference to a different place
      (``PROFILE.md`` vs ``SOUL.md`` vs ``~/.hermes/state.db``).
      Hard-coding a single ``OUTPUT_FILE`` unfairly zeroes whichever
      framework happens to differ.

    * Reward the *behavioural* signal that is reliably observable for
      every agent: the **transcript** (a normalised stream of message /
      toolCall events fed back to the grader by every backend).
      A persistence-style tool call whose arguments mention the
      preference content is the canonical evidence.  A Chinese
      acknowledgement in the final reply is the secondary evidence.

    * Filesystem evidence is treated as an *optional bonus* — present it
      when it happens, never punish its absence.

    Three independent checks (averaged):

      1. ``persisted_via_tool``    — saw a write/edit/memory tool call
         whose arguments mention the preference content.
      2. ``acknowledged_in_reply`` — final assistant text confirms the
         preference, in Chinese, with a "step by step" wording.
      3. ``preference_evidence``   — preference content found *either*
         in the tool-call arguments *or* in any common memory file
         (bonus signal; satisfied as long as evidence exists somewhere).
    """
    from pathlib import Path
    import json

    PREF_TOKENS = [
        "分步", "步骤", "逐步", "一步一步", "一步步",
        "step by step", "step-by-step", "step",
    ]
    PERSIST_TOOL_HINTS = (
        "edit", "write", "create_file", "patch", "apply",
        "memory", "remember", "save", "profile", "store",
    )
    OUTPUT_FILE_CANDIDATES = [
        "PROFILE.md", "USER.md", "MEMORY.md", "SOUL.md",
        "memory/USER.md", "memory/PROFILE.md",
        ".profile.md", ".memory.md",
    ]

    def has_pref_tokens(blob: str) -> bool:
        if not blob:
            return False
        low = blob.lower()
        return any(tok.lower() in low for tok in PREF_TOKENS)

    def iter_assistant_items(events):
        for e in events or []:
            if not isinstance(e, dict) or e.get("type") != "message":
                continue
            msg = e.get("message", {}) or {}
            if msg.get("role") != "assistant":
                continue
            for it in msg.get("content", []) or []:
                yield it

    scores = {}

    persisted = False
    pref_in_tool_args = False
    for it in iter_assistant_items(transcript):
        if not (isinstance(it, dict) and it.get("type") == "toolCall"):
            continue
        tool_name = (it.get("name") or "").lower()
        looks_like_persist = any(hint in tool_name for hint in PERSIST_TOOL_HINTS)
        try:
            args_blob = json.dumps(it.get("arguments", {}), ensure_ascii=False)
        except Exception:
            args_blob = str(it.get("arguments", ""))
        args_has_pref = has_pref_tokens(args_blob)

        if looks_like_persist and args_has_pref:
            persisted = True
            pref_in_tool_args = True
        elif args_has_pref:
            pref_in_tool_args = True
    scores["persisted_via_tool"] = 1.0 if persisted else 0.0

    final_text = ""
    for it in iter_assistant_items(transcript):
        if isinstance(it, dict) and it.get("type") == "text" and it.get("text"):
            final_text = it["text"]
    scores["acknowledged_in_reply"] = 1.0 if has_pref_tokens(final_text) else 0.0

    pref_in_file = False
    if workspace_path:
        ws = Path(workspace_path)
        for cand in OUTPUT_FILE_CANDIDATES:
            target = ws / cand
            if target.is_file() and target.stat().st_size > 0:
                try:
                    text = target.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    text = ""
                if has_pref_tokens(text):
                    pref_in_file = True
                    break
    scores["preference_evidence"] = 1.0 if (pref_in_tool_args or pref_in_file) else 0.0

    return scores
```

## LLM Judge Rubric

### task_completion (Weight: 50%)
Did the agent actually persist the preference *and* confirm it?

- 1.0: Transcript contains a persistence/memory tool call (e.g. `edit`,
  `write_file`, `memory`, `remember`, …) whose arguments include the
  "answer step by step" preference, AND the final reply explicitly
  acknowledges the preference in Chinese using a step-by-step wording.
- 0.75: Persistence happened and was acknowledged, but the wording is
  vague (e.g. acknowledges the request but doesn't restate the
  step-by-step facet).
- 0.5: Either the persistence happened but the acknowledgement is
  missing/in the wrong language, OR the agent only acknowledged in
  Chinese without any persistence tool call.
- 0.25: Acknowledgement only, with no persistence and no commitment
  to follow the preference; or persistence call exists but its
  arguments do not encode the preference content.
- 0.0: Neither persisted nor acknowledged; or the agent went off-task.

### tool_skill_use (Weight: 30%)
- 1.0: Exactly one appropriate persistence tool call with valid
  arguments; no wasted calls; reacts to the tool result before replying.
- 0.75: Mostly appropriate, with one minor inefficiency (e.g. a probing
  read before the write, or one redundant call).
- 0.5: Multiple wrong/wasted calls, or used a tool whose semantics do
  not actually persist the preference.
- 0.25: Tool use mostly absent or clearly incorrect.
- 0.0: No meaningful tool interaction at all (pure free-text reply).

### output_quality (Weight: 20%)
- 1.0: Confirmation is in Chinese, concise, and itself respects the
  declared preference (i.e. the acknowledgement does not contradict
  the "step by step" idea by piling on long unstructured text).
- 0.75: Confirmation is in Chinese with minor formatting issues.
- 0.5: Understandable but partially in the wrong language or format.
- 0.25: Confusing, off-topic, or contradicts the preference.
- 0.0: No usable final response.

Pass threshold: `total >= 0.6`.
