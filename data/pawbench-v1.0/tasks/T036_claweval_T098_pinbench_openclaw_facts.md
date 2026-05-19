---
id: T098_pinbench_openclaw_facts
name: Pinbench OpenClaw Facts
category: comprehension
grading_type: automated
timeout_seconds: 300
grading_weights:
  automated: 1.0
  llm_judge: 0.0
workspace_files:
- source: assets/T036_claweval_T098_pinbench_openclaw_facts/docs/openclaw_pinchbench.txt
  dest: docs/openclaw_pinchbench.txt
labels:
  capabilities:
  - Tool_Use
  modality:
    type: text
    channels: []
  scenario: Knowledge/QA
  complexity: L1
  environment: closed
---
## Prompt

Read `docs/openclaw_pinchbench.txt` and answer the eight questions below **in order, one per line**:

1. Total skills before filtering
2. Remaining skills after filtering
3. Largest category and count (format: `Name: count`)
4. Second-largest category and count
5. Skill definition file
6. Gateway API type
7. Data collection date
8. Number of proposed benchmark tasks

Save the 8-line answer to `output/answers.txt` (no extra prose, no numbering).

## Expected Behavior

The 8 expected answers (one per line, no blank lines):

```
5705
2999
AI & LLMs: 287
Search & Research: 253
SKILL.md
typed WebSocket API
February 7, 2026
6
```

(Variations like `5,705`, `5705 skills`, `Feb 7, 2026`, `2026-02-07` are acceptable.)

## Grading Criteria

- [ ] Read source document (file_read)
- [ ] Output file `output/answers.txt` exists (output_file_exists)
- [ ] Q1: 5705 (q1_total_before)
- [ ] Q2: 2999 (q2_remaining)
- [ ] Q3: AI & LLMs / 287 (q3_largest)
- [ ] Q4: Search & Research / 253 (q4_second_largest)
- [ ] Q5: SKILL.md (q5_skill_file)
- [ ] Q6: typed WebSocket API (q6_gateway)
- [ ] Q7: February 7, 2026 (q7_date)
- [ ] Q8: 6 (q8_tasks)

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    """
    Mirrors original PinbenchOpenClawFactsGrader formula exactly:
      checks = [tool_used, q1..q8]   (9 checks total)
      score = sum(checks) / len(checks)
    All checks are on final_text lines (output file preferred, transcript fallback).
    """

    def _all_text(msgs):
        parts = []
        for m in msgs:
            actual = m.get("message", m)
            if actual.get("role") not in ("assistant",):
                continue
            c = actual.get("content", "")
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, list):
                for b in c:
                    if isinstance(b, dict):
                        parts.append(b.get("text", ""))
        return " ".join(parts)

    transcript_text = _all_text(transcript)
    output_path = Path(workspace_path) / "output" / "answers.txt"
    file_content = ""
    if output_path.is_file():
        try:
            file_content = output_path.read_text(encoding="utf-8")
        except Exception:
            pass

    # Use output file lines for answer checks (mirrors original lines[] logic)
    review_text = file_content if file_content else transcript_text
    lines = [ln.strip() for ln in review_text.splitlines() if ln.strip()]

    def _line(i):
        return lines[i] if i < len(lines) else ""

    combined_lower = (transcript_text + " " + file_content).lower()

    # tool_used: agent read the document (proxy for documents_extract_text)
    tool_used = bool(re.search(r"openclaw_pinchbench\.txt|documents_extract_text", combined_lower))

    # 8 answer checks — identical logic to original grader
    checks = [
        tool_used,
        len(lines) >= 1 and "5705" in _line(0).replace(",", ""),
        len(lines) >= 2 and "2999" in _line(1).replace(",", ""),
        len(lines) >= 3 and "ai" in _line(2).lower() and "287" in _line(2),
        len(lines) >= 4 and "search" in _line(3).lower() and "253" in _line(3),
        len(lines) >= 5 and "skill.md" in _line(4).lower(),
        len(lines) >= 6 and "websocket" in _line(5).lower() and "typed" in _line(5).lower(),
        len(lines) >= 7 and bool(re.search(r"feb.*7.*2026|2026.*02.*07", _line(6).lower())),
        len(lines) >= 8 and _line(7).strip() == "6",
    ]

    return {"score": round(sum(1.0 if c else 0.0 for c in checks) / len(checks), 3)}
```

## LLM Judge Rubric

> **注意：本任务 grading_type 为 automated，LLM judge 权重为 0。实际评分由 Automated Checks 决定。**

原始 grader 为纯规则评分：`score = sum(9项check) / 9`
- check[0]: 读取了文档（tool_used）
- check[1..8]: 8个答案按行精确匹配
