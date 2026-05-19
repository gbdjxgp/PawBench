---
id: T088_pinbench_project_bootstrap_plan
name: Pinbench Project Bootstrap Plan
category: file_ops
grading_type: automated
timeout_seconds: 300
grading_weights:
  automated: 1.0
  llm_judge: 0.0
labels:
  capabilities:
  - Tool_Use
  - Planning
  modality:
    type: text
    channels: []
  scenario: Office_Productivity/Task_Management
  complexity: L2
  environment: closed
---
## Prompt

Instead of creating files directly, **bootstrap** a Python library project plan for **"datautils"**. Create actionable tasks for:

1. Creating the package structure under `src/datautils`
2. Adding tests (under `tests/`)
3. Writing `pyproject.toml` metadata
4. Writing a `README`

Save the task list as JSON to `output/bootstrap_plan.json` with this structure:
```json
{
  "tasks": [
    {"title": "Create src/datautils package structure", "description": "...", "priority": "high"},
    {"title": "Add tests under tests/", "description": "...", "priority": "high"},
    {"title": "Write pyproject metadata", "description": "...", "priority": "medium"},
    {"title": "Write README", "description": "...", "priority": "medium"}
  ],
  "summary": "..."
}
```

Then summarize the setup plan in your final response.

## Expected Behavior

Create exactly 4 tasks covering:
1. Package structure under `src/datautils`
2. Tests under `tests/`
3. `pyproject.toml` metadata
4. `README`

Each task should have a clear title, description, and priority. The summary should explain the plan.

## Grading Criteria

- [ ] Output file `output/bootstrap_plan.json` exists (output_file_exists)
- [ ] At least 4 tasks listed (tasks_count)
- [ ] All 4 expected items covered (`src/datautils`, `tests`, `pyproject`, `README`) (items_covered)
- [ ] Final summary mentions the plan (summary_present)

## Automated Checks

```python
import json
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    """
    Mirrors original PinbenchProjectBootstrapPlanGrader formula exactly:
      create_count_score = min(len(create_calls) / 4, 1.0)
      hit_ratio          = expected items found in task titles / 4
      summary_ratio      = expected items found in final_text / 4
      score = (create_count_score + hit_ratio + summary_ratio) / 3
    Output JSON tasks serve as proxy for todo_create_task API calls.
    Final transcript text serves as proxy for final_assistant_text.
    """

    EXPECTED = ["src/datautils", "tests", "pyproject", "README"]

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
    output_path = Path(workspace_path) / "output" / "bootstrap_plan.json"
    file_content = ""
    payload = None
    if output_path.is_file():
        try:
            file_content = output_path.read_text(encoding="utf-8")
            payload = json.loads(file_content)
        except Exception:
            pass

    tasks = []
    if isinstance(payload, dict):
        tasks = payload.get("tasks") or []
    if not isinstance(tasks, list):
        tasks = []

    # create_count_score: proxy for "how many todo_create_task calls were made"
    create_count_score = min(len(tasks) / 4, 1.0)

    # hit_ratio: expected items found in task titles (mirrors original "titles" variable)
    titles = " ".join(str(t.get("title", "")) for t in tasks if isinstance(t, dict))
    titles_lower = titles.lower()
    hit_ratio = sum(1 for item in EXPECTED if item.lower() in titles_lower) / len(EXPECTED)

    # summary_ratio: expected items found in final response (mirrors original "final_text")
    final_lower = transcript_text.lower()
    summary_ratio = sum(1 for item in EXPECTED if item.lower() in final_lower) / len(EXPECTED)

    score = round((create_count_score + hit_ratio + summary_ratio) / 3, 3)
    return {"score": score}
```

## LLM Judge Rubric

> **注意：本任务 grading_type 为 automated，LLM judge 权重为 0。实际评分由 Automated Checks 决定。**

原始 grader 为纯规则评分：`score = (create_count_score + hit_ratio + summary_ratio) / 3`
- create_count_score = min(任务数 / 4, 1.0)
- hit_ratio = EXPECTED 中出现在 task titles 的比例
- summary_ratio = EXPECTED 中出现在 final_text 的比例
