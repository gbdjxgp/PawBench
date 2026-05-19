---
id: T126_meeting_action_items
name: Meeting Action Item Extraction and Deduplication
category: workflow
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.2
  llm_judge: 0.8
workspace_files:
- source: assets/T040_claweval_T126_meeting_action_items/notes/meetings.json
  dest: notes/meetings.json
- source: assets/T040_claweval_T126_meeting_action_items/todo/tasks.json
  dest: todo/tasks.json
labels:
  capabilities:
  - Tool_Use
  - Planning
  - Logic_Reasoning
  - Self_Verification
  modality:
    type: text
    channels: []
  scenario: Office_Productivity/Meeting
  complexity: L3
  environment: closed
---
## Prompt

We've had several important meetings recently. Please help me:

1. Review all meeting notes in `notes/meetings.json` and extract the action items from them
2. Check the current to-do list in `todo/tasks.json`
3. Compare the meeting action items with existing to-dos to identify ones that already have a corresponding to-do (to avoid creating duplicates)
4. List the action items that need new to-dos created
5. Output a complete action item tracking table (including source meeting, assignee, due date, and whether a to-do already exists)
6. Save the final tracking result as JSON to `output/action_items.json`

## Expected Behavior

1. Read `notes/meetings.json` → 3 meeting notes (NOTE-301, NOTE-302, NOTE-303) with 9 total action items
2. Read `todo/tasks.json` → 5 existing to-do items (TODO-401 through TODO-405)
3. Extract all 9 action items:
   - NOTE-301: Wang Ming (Q2 roadmap, 3/28), Li Hua (competitor research, 3/30), Zhao Lei (customer requirements, 3/27), Zhang Wei (security assessment, 3/31)
   - NOTE-302: Li Hua (microservice plan, 4/3), Ma Qiang (DB migration test env, 3/28), Zhou Ming (frontend component upgrade, 4/5)
   - NOTE-303: Wang Ming (Q1 performance summary, 3/29), Zhao Lei (renewal strategy, 3/30)
4. Match fuzzy duplicates:
   - Action item 1 ↔ TODO-401 (same assignee + topic, different wording)
   - Action item 3 ↔ TODO-402 (same assignee + topic, different wording)
   - Action item 6 ↔ TODO-403 (same assignee + topic, different wording)
   - TODO-404 (standup) and TODO-405 (deployment docs) are unrelated
5. Output: 9 action items, 3 with existing to-dos matched, 6 needing new to-dos

## Grading Criteria

- [ ] Read both `notes/meetings.json` AND `todo/tasks.json` (tool usage gate — applies 0.5× penalty if fewer than 2 notes processed, 0.6× if todo not consulted)
- [ ] Extracted all 9 action items from 3 meeting notes (weight=0.35)
- [ ] Correctly identified 3 fuzzy matches with existing to-dos: TODO-401, 402, 403 (weight=0.35)
- [ ] Listed 6 action items that need new to-dos with assignee + due date (weight=0.30)
- [ ] Did not falsely match TODO-404 or TODO-405

## Automated Checks

```python
import json
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "output_file_exists": 0.0,
        "notes_coverage": 0.0,    # meeting notes data read
        "todo_coverage": 0.0,     # todo list data read
        "all_items_extracted": 0.0,  # 9 action items extracted
        "correct_matches": 0.0,   # 3 correct fuzzy matches
        "no_false_matches": 1.0,  # no false matches for TODO-404/405
        "new_todos_listed": 0.0,  # 6 new to-dos recommended
    }

    def _all_text(msgs: list) -> str:
        parts = []
        for m in msgs:
            actual = m.get("message", m)
            if actual.get("role") not in ("assistant",):
                continue
            content = actual.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        parts.append(block.get("text", ""))
        return " ".join(parts)

    transcript_text = _all_text(transcript)

    # Read output file if it exists
    output_path = Path(workspace_path) / "output" / "action_items.json"
    file_content = ""
    if output_path.is_file():
        result["output_file_exists"] = 1.0
        try:
            file_content = output_path.read_text(encoding="utf-8")
        except Exception:
            pass

    combined = transcript_text + " " + file_content

    # Meeting notes coverage: action items or names from notes should appear
    note_signals = [
        bool(re.search(r"NOTE-30[123]", combined)),
        bool(re.search(r"Wang Ming|Wang\s+Ming", combined)),
        bool(re.search(r"Li Hua|Li\s+Hua", combined)),
        bool(re.search(r"Zhao Lei|Zhao\s+Lei", combined)),
        bool(re.search(r"Q2.*roadmap|product roadmap|产品路线图", combined, re.IGNORECASE)),
        bool(re.search(r"microservice|微服务", combined, re.IGNORECASE)),
    ]
    result["notes_coverage"] = sum(note_signals) / len(note_signals)

    # Todo list coverage: TODO IDs should appear
    todos_found = set(re.findall(r"TODO-40[1-5]", combined))
    if len(todos_found) >= 3:
        result["todo_coverage"] = 1.0
    elif len(todos_found) >= 1:
        result["todo_coverage"] = len(todos_found) / 5

    # Action items extracted: check for key names + dates from all 3 notes
    extraction_signals = [
        bool(re.search(r"3/28|3-28|March 28", combined, re.IGNORECASE)),   # NOTE-301 item 1
        bool(re.search(r"3/30|3-30|March 30", combined, re.IGNORECASE)),   # NOTE-301 item 2
        bool(re.search(r"3/27|3-27|March 27", combined, re.IGNORECASE)),   # NOTE-301 item 3
        bool(re.search(r"3/31|3-31|March 31", combined, re.IGNORECASE)),   # NOTE-301 item 4
        bool(re.search(r"4/3|4-3|April 3", combined, re.IGNORECASE)),      # NOTE-302 item 5
        bool(re.search(r"4/5|4-5|April 5", combined, re.IGNORECASE)),      # NOTE-302 item 7
        bool(re.search(r"3/29|3-29|March 29", combined, re.IGNORECASE)),   # NOTE-303 item 8
        bool(re.search(r"Zhang Wei|Zhang\s+Wei", combined)),
        bool(re.search(r"Ma Qiang|Ma\s+Qiang", combined)),
        bool(re.search(r"Zhou Ming|Zhou\s+Ming", combined)),
    ]
    result["all_items_extracted"] = sum(extraction_signals) / len(extraction_signals)

    # Correct matches: TODO-401, 402, 403 identified as matches
    matched = todos_found & {"TODO-401", "TODO-402", "TODO-403"}
    result["correct_matches"] = len(matched) / 3

    # No false matches: TODO-404 and TODO-405 should NOT be flagged as matches
    false_match_pattern = r"(?:match|correspond|duplicate|existing).{0,200}TODO-40[45]|TODO-40[45].{0,200}(?:match|correspond)"
    if re.search(false_match_pattern, combined, re.IGNORECASE):
        result["no_false_matches"] = 0.0

    # New to-dos: 6 new recommendations should be listed
    # Look for 6 assignees appearing with new/create/need context
    new_todo_signals = [
        bool(re.search(r"Li Hua.{0,100}competitor|competitor.{0,100}Li Hua", combined, re.IGNORECASE)),
        bool(re.search(r"Zhang Wei.{0,100}security|security.{0,100}Zhang Wei", combined, re.IGNORECASE)),
        bool(re.search(r"Li Hua.{0,100}microservice|microservice.{0,100}Li Hua", combined, re.IGNORECASE)),
        bool(re.search(r"Zhou Ming.{0,100}frontend|frontend.{0,100}Zhou Ming", combined, re.IGNORECASE)),
        bool(re.search(r"Wang Ming.{0,100}performance|performance.{0,100}Wang Ming", combined, re.IGNORECASE)),
        bool(re.search(r"Zhao Lei.{0,100}renewal|renewal.{0,100}Zhao Lei", combined, re.IGNORECASE)),
    ]
    result["new_todos_listed"] = sum(new_todo_signals) / len(new_todo_signals)

    return result
```

## LLM Judge Rubric

### Criterion 1: Extraction Completeness (Weight: 35%)

Evaluate the completeness of the assistant's action item extraction (0.0–1.0).

**9 Action Items from 3 Meeting Notes:**

NOTE-301 (4 items):
1. Wang Ming — Q2 product roadmap document, due 3/28
2. Li Hua — Competitor new feature research report, due 3/30
3. Zhao Lei — Top 10 customer requirements list, due 3/27
4. Zhang Wei — Security compliance assessment report, due 3/31

NOTE-302 (3 items):
5. Li Hua — Microservice decomposition technical plan, due 4/3
6. Ma Qiang — Database migration test environment, due 3/28
7. Zhou Ming — Frontend component library upgrade to v3.0, due 4/5

NOTE-303 (2 items):
8. Wang Ming — Q1 technical team performance summary, due 3/29
9. Zhao Lei — Key customer renewal strategy proposal, due 3/30

**Strict scoring:**
- **1.0**: All 9 action items extracted, with assignee and due date for each
- **0.7–0.8**: 7–8 extracted with assignee and due date
- **0.4–0.6**: 5–6 extracted
- **0.0–0.3**: Fewer than 5 extracted

---

### Criterion 2: Deduplication Accuracy (Weight: 35%)

Evaluate the accuracy of the assistant's deduplication matching between action items and to-dos (0.0–1.0).

**Correct 3 Fuzzy Matches:**
1. Action item "Q2 product roadmap document" (Wang Ming) ↔ TODO-401 "Complete product roadmap" (Wang Ming)
   — Match basis: same assignee + same topic + same due date (3/28)
2. Action item "Top 10 customer requirements list" (Zhao Lei) ↔ TODO-402 "Compile customer requirements" (Zhao Lei)
   — Match basis: same assignee + overlapping topic + same due date (3/27)
3. Action item "Database migration test environment" (Ma Qiang) ↔ TODO-403 "DB migration test environment setup" (Ma Qiang)
   — Match basis: same assignee + same topic (DB = database) + same due date (3/28)

**Should NOT match:**
- TODO-404 (standup meetings) and TODO-405 (deployment documentation) are unrelated to any action item
- The remaining 6 action items have no corresponding to-do

**Strict scoring:**
- **1.0**: All 3 matches correct, no false matches with TODO-404 or TODO-405
- **0.6–0.8**: 2 correct matches, no false matches
- **0.3–0.5**: 1 correct match
- **0.0–0.2**: Matches incorrect or deduplication not performed

---

### Criterion 3: New To-Do Recommendations (Weight: 30%)

Evaluate the completeness of new to-do suggestions (0.0–1.0).

**6 New To-Dos Needed:**
1. Li Hua — Competitor new feature research report (due 3/30, source NOTE-301)
2. Zhang Wei — Security compliance assessment report (due 3/31, source NOTE-301)
3. Li Hua — Microservice decomposition technical plan (due 4/3, source NOTE-302)
4. Zhou Ming — Frontend component library upgrade to v3.0 (due 4/5, source NOTE-302)
5. Wang Ming — Q1 technical team performance summary (due 3/29, source NOTE-303)
6. Zhao Lei — Key customer renewal strategy proposal (due 3/30, source NOTE-303)

**Suggestions should include:** assignee, due date, source meeting, suggested priority.

**Strict scoring:**
- **1.0**: All 6 new suggestions listed with complete information (assignee + due date + source)
- **0.6–0.8**: 4–5 suggestions listed with complete information
- **0.3–0.5**: 2–3 suggestions listed
- **0.0–0.2**: Fewer than 2 suggestions
