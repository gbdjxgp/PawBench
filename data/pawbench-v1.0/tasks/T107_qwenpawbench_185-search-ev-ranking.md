---
id: 185-search-ev-ranking
name: Search Ev Ranking
category: web-search
grading_type: hybrid
grading_weights:
  automated: 0.5
  llm_judge: 0.5
timeout_seconds: 600
input_modality: text-only
external_dependency: none
origin_benchmark: pawbench
origin_task_id: 185-search-ev-ranking
complexity: L1
copaw:
  required_tools: []
  required_skills: []
  distractor_skills: []
labels:
  scenario: Information_Retrieval/Market
  complexity: L2
  environment: open
  modality:
    type: text
  capabilities:
  - Tool_Use
---

## Prompt

搜一下 2026 年国内新能源汽车销量排行，哪几款车型卖得最好？

## Expected Behavior

The agent should fulfil the user request above using only appropriate tools and skills, and produce the requested artefact / answer.

## Grading Criteria

- Task is fully completed as requested
- Tool / skill usage is appropriate and efficient
- Final response is clear, accurate, and in the requested format

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    """Auto-converted PawBench grader — session/trajectory style task.

    Checks:
      - agent_responded : agent produced a final assistant text
      - used_tools      : agent called at least one tool
      - keywords_match  : (if KEYWORDS) any keyword appears in the final reply
                          OR in the JSON-serialised arguments of any tool call
                          OR in the text of any tool result.  This handles
                          cron-style tasks where the relevant text lives inside
                          a tool argument rather than the final reply.
    """
    import json as _json

    KEYWORDS = []

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

    def final_text(events):
        last = ""
        for m in iter_messages(events, "assistant"):
            for it in m.get("content", []) or []:
                if isinstance(it, dict) and it.get("type") == "text" and it.get("text"):
                    last = it["text"]
        return last

    def all_searchable_text(events):
        chunks = []
        for m in iter_messages(events, "assistant"):
            for it in m.get("content", []) or []:
                if isinstance(it, dict) and it.get("type") == "text" and it.get("text"):
                    chunks.append(it["text"])
                elif isinstance(it, dict) and it.get("type") == "toolCall":
                    args = it.get("arguments") or {}
                    try:
                        chunks.append(_json.dumps(args, ensure_ascii=False))
                    except Exception:
                        chunks.append(str(args))
        for m in iter_messages(events, "toolResult"):
            for it in m.get("content", []) or []:
                if isinstance(it, str):
                    chunks.append(it)
                elif isinstance(it, dict) and it.get("text"):
                    chunks.append(str(it["text"]))
        return "\n".join(chunks)

    scores = {}
    scores["agent_responded"] = 1.0 if final_text(transcript).strip() else 0.0
    scores["used_tools"] = 1.0 if any(iter_tool_calls(transcript)) else 0.0
    if KEYWORDS:
        haystack = all_searchable_text(transcript).lower()
        hits = [kw for kw in KEYWORDS if kw.lower() in haystack]
        scores["keywords_match"] = 1.0 if hits else 0.0
    return scores
```

## LLM Judge Rubric

### task_completion (Weight: 50%)
- 1.0: Fully accomplishes the user's request (correct artefact, correct answer, correct preference recorded), no missing piece.
- 0.75: Mostly accomplishes the goal; minor omissions or imprecision.
- 0.5: Partial completion or correct intent but flawed execution.
- 0.25: Tries but fails most acceptance criteria.
- 0.0: Does not address the request.

### tool_skill_use (Weight: 30%)
- 1.0: Uses appropriate tools/skills with valid arguments and reacts to results.
- 0.75: Mostly appropriate with one wrong call or minor inefficiency.
- 0.5: Several wrong choices or wasted calls.
- 0.25: Tool use mostly incorrect or absent.
- 0.0: No meaningful tool interaction.

### output_quality (Weight: 20%)
- 1.0: Final response is clear, well-structured, in the requested language/format, and accurate.
- 0.75: Mostly clear with minor formatting or content gaps.
- 0.5: Understandable but incomplete or partially incorrect.
- 0.25: Confusing or off-topic response.
- 0.0: No usable final response.

Pass threshold: `total >= 0.6`.
