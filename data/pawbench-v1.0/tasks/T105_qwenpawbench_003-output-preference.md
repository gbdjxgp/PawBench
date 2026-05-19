---
id: 003-output-preference
name: Output Preference
category: memory
grading_type: hybrid
grading_weights:
  automated: 0.5
  llm_judge: 0.5
timeout_seconds: 300
input_modality: text-only
external_dependency: none
origin_benchmark: pawbench
origin_task_id: 003-output-preference
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
    channels: []
  capabilities:
  - Tool_Use
---

## Prompt

记住，我喜欢所有输出都用中文，表格用markdown格式。

## Expected Behavior

The user is teaching the agent a long-term **output style preference**:

1. All future replies must be written in **Chinese**.
2. Whenever a table is needed, it must be rendered as a **Markdown table**
   (i.e. pipe-separated `|` columns with a `---` header separator), not as
   plain text, HTML, ASCII art or an image.

A correct run must satisfy **all** of the following:

- **Persist the preference.** The agent must invoke a persistence/memory
  tool call whose arguments contain the preference content (mentioning at
  least the language requirement *and* the markdown-table requirement).
  Different agent frameworks expose this differently — e.g. an `edit` /
  `write_file` call that appends the preference into a memory markdown
  file (`PROFILE.md`, `USER.md`, `MEMORY.md`, …), or a dedicated
  `memory` / `remember` tool that writes into the agent's own memory
  store. Any of these is acceptable as long as the tool call actually
  happens and its arguments encode the preference.
  Merely *saying* "好的，我记住了" without any persistence tool call
  does **not** satisfy this requirement.

- **Acknowledge the preference in the reply.** The final assistant
  message must confirm in Chinese that the preference has been recorded,
  and the confirmation itself should already follow the preference
  (Chinese language; if the agent chooses to summarise the preference as
  a list/table, the table must be in Markdown).

- **No off-task actions.** The agent should not start producing unrelated
  artefacts (the user only asked it to remember the preference, not to
  perform another task).

It is *not* required that the preference be visible in any specific file
on the workspace filesystem — some agents persist memory inside an
internal store (SQLite, JSON in the agent's home directory, etc.).
Evidence in the transcript (a tool call with the right arguments + a
Chinese acknowledgement) is sufficient.

## Grading Criteria

- [ ] Agent invoked a persistence/memory tool with arguments encoding both the Chinese-output and Markdown-table preferences.
- [ ] Final assistant reply confirms the preference in Chinese.
- [ ] No unrelated tool calls or off-task output.

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """Lenient, agent-neutral checks for the "remember my output preference" task.

    Design goals:

    * Don't hard-code any agent-specific filesystem layout.  Different
      agent frameworks persist user preferences differently — copaw /
      openclaw write into ``PROFILE.md`` / ``USER.md`` inside the
      workspace, while hermes writes into ``~/.hermes/state.db``
      (SQLite, not visible from ``workspace_path``).  Hard-coding a file
      list unfairly penalises whichever framework happens to differ.

    * Reward the *behavioural* signal that is reliably observable for
      every agent: the **transcript** (a normalised stream of message /
      toolCall / toolResult events fed back to the grader by every
      backend).  If the transcript shows a persistence-style tool call
      whose arguments mention the preference, credit it.  If the final
      reply also acknowledges the preference, credit it.

    * Filesystem evidence is treated as an *optional bonus* — present it
      when it happens, never punish its absence.

    Three independent checks (averaged):

      1. ``persisted_via_tool``    — saw a write/edit/memory tool call
         whose arguments mention the preference content.
      2. ``acknowledged_in_reply`` — final assistant text confirms the
         preference, in Chinese.
      3. ``preference_evidence``   — preference content found *either*
         in the tool-call arguments *or* in any common memory file
         (bonus signal; satisfied as long as evidence exists somewhere).
    """
    from pathlib import Path
    import json

    PREF_TOKENS = ["中文", "汉语", "Chinese", "markdown", "Markdown"]
    PERSIST_TOOL_HINTS = (
        "edit", "write", "create_file", "patch", "apply",
        "memory", "remember", "save", "profile", "store",
    )
    OUTPUT_FILE_CANDIDATES = [
        "PROFILE.md", "USER.md", "MEMORY.md",
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
  `write_file`, `memory`, `remember`, …) whose arguments include both
  the Chinese-language preference and the Markdown-table preference,
  AND the final reply explicitly acknowledges the preference in Chinese.
- 0.75: Persistence happened and was acknowledged, but one of the two
  preference facets is missing or paraphrased loosely (e.g. only
  "中文" is recorded, "markdown 表格" omitted).
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
  declared preferences (Chinese; any table is Markdown).
- 0.75: Confirmation is in Chinese with minor formatting issues (e.g.
  partial English fragments, or a non-Markdown bullet list when a table
  was natural).
- 0.5: Understandable but partially in the wrong language or format.
- 0.25: Confusing, off-topic, or contradicts the preference.
- 0.0: No usable final response.

Pass threshold: `total >= 0.6`.
