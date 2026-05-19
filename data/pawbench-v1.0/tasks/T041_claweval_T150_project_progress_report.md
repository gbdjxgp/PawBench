---
id: T150_project_progress_report
name: Parallel Project Progress Report Generation
category: workflow
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.2
  llm_judge: 0.8
workspace_files:
- source: assets/T041_claweval_T150_project_progress_report/calendar/events.json
  dest: calendar/events.json
- source: assets/T041_claweval_T150_project_progress_report/notes/meetings.json
  dest: notes/meetings.json
- source: assets/T041_claweval_T150_project_progress_report/todo/tasks.json
  dest: todo/tasks.json
- source: assets/T041_claweval_T150_project_progress_report/contacts/contacts.json
  dest: contacts/contacts.json
labels:
  capabilities:
  - Tool_Use
  - Planning
  - Logic_Reasoning
  - Math_Computation
  - Self_Verification
  modality:
    type: text
    channels: []
  scenario: Office_Productivity/Task_Management
  complexity: L3
  environment: closed
---
## Prompt

Please help me generate progress reports for 3 parallel projects (Alpha/Beta/Gamma):

1. Review `calendar/events.json` to find the relevant meetings for each project
2. Read action items from `notes/meetings.json` for the meeting notes linked to each project
3. Check to-do completion status in `todo/tasks.json`
4. Look up project lead contact information in `contacts/contacts.json`
5. Produce a progress report for each of the 3 projects, marking risk items
6. Save the final combined report as JSON to `output/progress_report.json`

## Expected Behavior

**Alpha Project (~75% progress, on track)**
- Meetings: evt_601 (requirements review 3/17) + evt_602 (technical design 3/20)
- Notes: NOTE-601 (3 action items: 2 done + 1 in-progress) + NOTE-602 (2 action items: 1 done + 1 not started)
- To-dos: TODO-601 ✓, TODO-602 ✓, TODO-603 in_progress, TODO-604 ✓ → 3/4 done = 75%
- Leads: Wang Ming (project manager), Li Hua (architect), Ma Qiang (ops)
- Risk: TODO-603 (technical feasibility report, due 3/25) still in progress; microservice architecture plan depends on it

**Beta Project (~45% progress, delayed, high risk)**
- Meetings: evt_603 (kickoff 3/18) + evt_604 (progress check 3/22)
- Notes: NOTE-603 (3 items: 1 done + 1 in-progress + 1 blocked) + NOTE-604 (2 items: both pending, 1 overdue)
- To-dos: TODO-605 ✓, TODO-606 in_progress, TODO-607 pending/blocked, TODO-608 pending, TODO-609 in_progress → 1/5 = 20% task done rate
- Leads: Zhao Lei (product manager), Zhang Wei (backend dev), Zhou Ming (frontend dev)
- Critical risks: TODO-607 frontend prototype blocked (waiting for third-party API docs, overdue 3/22); TODO-608 API dev depends on incomplete DB design; ~1 week behind

**Gamma Project (~90%+, near completion)**
- Meetings: evt_605 (client meeting 3/19) + evt_606 (delivery review 3/24, **no meeting notes!**)
- Notes: NOTE-605 (2 items: both done); evt_606 has no corresponding notes
- To-dos: TODO-610 ✓, TODO-611 ✓, TODO-612 ✓ → 3/3 done = 100%
- Leads: Wang Ming (project manager), Zhao Lei (product manager)
- Notable: evt_606 (3/24 delivery review) is missing notes — needs follow-up

## Grading Criteria

- [ ] Read all 4 data files: calendar, notes, todo, contacts (tool usage gate — see penalties below)
- [ ] Correctly classified meetings across Alpha/Beta/Gamma (evt_601–606)
- [ ] Identified that evt_606 (Gamma delivery review) has no meeting notes
- [ ] Alpha progress ~75% with TODO-603 as the risk item
- [ ] Beta project identified as delayed/high-risk with the third-party API block as core bottleneck
- [ ] Gamma project near completion (~90%+)
- [ ] Lead contact information included for each project
- [ ] Risk annotations present in the reports

**Tool usage gate (automated, multiplicative penalties):**
- < 3 of 5 notes read (NOTE-601–605) → ×0.5
- Todos not queried → ×0.5
- Contacts not queried → ×0.6
- Calendar not queried → ×0.6

## Automated Checks

```python
import json
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "output_file_exists": 0.0,
        "three_projects_covered": 0.0,
        "alpha_progress": 0.0,     # Alpha ~75%, on track
        "beta_risks_found": 0.0,   # Beta delayed/blocked
        "gamma_progress": 0.0,     # Gamma ~90%+ near completion
        "contacts_included": 0.0,  # Lead contact info present
        "missing_notes_flagged": 0.0,  # evt_606 missing notes flagged
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
    output_path = Path(workspace_path) / "output" / "progress_report.json"
    file_content = ""
    if output_path.is_file():
        result["output_file_exists"] = 1.0
        try:
            file_content = output_path.read_text(encoding="utf-8")
        except Exception:
            pass

    combined = transcript_text + " " + file_content

    # All 3 project names must appear
    has_alpha = bool(re.search(r"\bAlpha\b", combined, re.IGNORECASE))
    has_beta = bool(re.search(r"\bBeta\b", combined, re.IGNORECASE))
    has_gamma = bool(re.search(r"\bGamma\b", combined, re.IGNORECASE))
    result["three_projects_covered"] = (has_alpha + has_beta + has_gamma) / 3

    # Alpha progress: ~75%, on track, technical feasibility risk
    alpha_signals = [
        bool(re.search(r"75%|3/4|75 percent", combined, re.IGNORECASE)),
        bool(re.search(r"on track|按时|按计划", combined, re.IGNORECASE)),
        bool(re.search(r"TODO-603|technical feasibility|技术可行性", combined, re.IGNORECASE)),
    ]
    result["alpha_progress"] = sum(alpha_signals) / len(alpha_signals)

    # Beta risks: delayed, blocked, third-party API dependency
    beta_signals = [
        bool(re.search(r"delay|behind|滞后|延迟|落后", combined, re.IGNORECASE)),
        bool(re.search(r"block|阻塞|blocked", combined, re.IGNORECASE)),
        bool(re.search(r"third.party|第三方|API doc", combined, re.IGNORECASE)),
        bool(re.search(r"TODO-607|frontend.*prototype|原型", combined, re.IGNORECASE)),
        bool(re.search(r"high.risk|高风险|critical risk", combined, re.IGNORECASE)),
    ]
    result["beta_risks_found"] = sum(beta_signals) / len(beta_signals)

    # Gamma progress: near completion, ~90%+
    gamma_signals = [
        bool(re.search(r"100%|3/3|complete|完成", combined, re.IGNORECASE)),
        bool(re.search(r"near completion|即将完成|接近完成", combined, re.IGNORECASE)),
        bool(re.search(r"90%|delivery|交付", combined, re.IGNORECASE)),
    ]
    result["gamma_progress"] = sum(gamma_signals) / len(gamma_signals)

    # Contacts: lead names + role or email/phone
    contact_signals = [
        bool(re.search(r"Wang Ming|Wang\s+Ming", combined)),
        bool(re.search(r"Zhao Lei|Zhao\s+Lei", combined)),
        bool(re.search(r"Zhang Wei|Zhang\s+Wei", combined)),
        bool(re.search(r"@company\.com|\d{11}|project manager|architect", combined, re.IGNORECASE)),
    ]
    result["contacts_included"] = sum(contact_signals) / len(contact_signals)

    # Missing notes for Gamma's evt_606 delivery review
    missing_signals = [
        bool(re.search(r"evt_606", combined)),
        bool(re.search(r"missing|no notes|没有.*纪要|缺少.*纪要|缺少.*记录", combined, re.IGNORECASE)),
        bool(re.search(r"3/24|March 24|delivery review", combined, re.IGNORECASE)),
    ]
    # Require at least 2 of 3 signals
    hit = sum(missing_signals)
    if hit >= 2:
        result["missing_notes_flagged"] = 1.0
    elif hit == 1:
        result["missing_notes_flagged"] = 0.4

    return result
```

## LLM Judge Rubric

### Criterion 1: Progress Data Accuracy (Weight: 35%)

Evaluate the accuracy of progress data for three projects (0.0–1.0).

**Alpha Project (Progress ~75%, on track):**
- To-dos (4): TODO-601 completed, TODO-602 completed, TODO-603 in_progress, TODO-604 completed → 3/4 = 75%
- Action items: 5 total (NOTE-601: 3 items, NOTE-602: 2 items), 3 completed / 1 in progress / 1 not started
- Status: on track; technical feasibility report in progress

**Beta Project (Progress ~20–45%, severely delayed):**
- To-dos (5): TODO-605 completed, TODO-606 in_progress, TODO-607 pending (blocked), TODO-608 pending, TODO-609 in_progress → 1/5 = 20% task completion rate; overall ~30–45%
- Action items: 5 total (NOTE-603: 3 items, NOTE-604: 2 items), 1 completed / 2 in_progress or blocked / 2 pending
- Status: delayed ~1 week, has blocked items

**Gamma Project (Progress ~90–100%, near completion):**
- To-dos (3): TODO-610, TODO-611, TODO-612 all completed → 3/3 = 100%
- Action items: 2 total (NOTE-605), both completed; but evt_606 (delivery review 3/24) has no meeting notes → overall ~90%
- Status: near completion

**Strict scoring:**
- **1.0**: All three projects' progress data accurate, completion rates correctly calculated from to-do and action item data
- **0.7–0.8**: At least 2 projects' progress accurate; one project off by more than 20 percentage points
- **0.4–0.6**: At least 1 project accurate, others roughly correct direction
- **0.0–0.3**: Progress data seriously wrong or missing for most projects

---

### Criterion 2: Risk Identification (Weight: 35%)

Evaluate the completeness and accuracy of risk identification (0.0–1.0).

**Risks that MUST be identified:**

Beta Project Critical Risks (most important):
1. TODO-607 Frontend prototype design **blocked** — waiting for third-party API docs, already overdue (due 3/22)
2. TODO-608 API development pending (high priority) — depends on unfinished database design (TODO-606)
3. Overall progress behind by **~1 week** (NOTE-604 meeting conclusion explicitly states this)
4. Third-party API documentation block is the **core bottleneck**, affecting both frontend and backend

Alpha Project Attention:
5. TODO-603 Technical feasibility report due 3/25, still in progress — needs monitoring
6. NOTE-602 action item 2 (microservice architecture plan) depends on the feasibility report — cascading dependency

Gamma Project Attention:
7. **evt_606** (3/24 delivery review) has no meeting notes — needs follow-up

**Strict scoring:**
- **1.0**: All Beta core risks (1–4) identified AND Gamma's missing notes (7) flagged
- **0.7–0.8**: Beta main risks identified (at least 3 of 4); Gamma missing notes may be absent
- **0.4–0.6**: Some risks identified but incomplete (e.g., mentions Beta is delayed but misses third-party API root cause)
- **0.0–0.3**: Critical Beta risks not identified

---

### Criterion 3: Report Completeness (Weight: 30%)

Evaluate the completeness and professionalism of the progress report (0.0–1.0).

**A qualifying report should include all 7 elements:**
1. Structured report grouped by project (one section each for Alpha/Beta/Gamma)
2. Meeting list and note summaries for each project
3. Action item checklist with completion status comparison
4. To-do completion rate statistics (e.g., "3/4 = 75%")
5. Project leads and contact information (email and/or phone preferred)
6. Risk annotations and recommendations
7. Priority or attention ranking across projects (Beta needs most attention)

**Lead contact information (from contacts.json):**
- Wang Ming (Project Manager): wangming@company.com, 13900139001 → Alpha, Gamma
- Li Hua (Architect): lihua@company.com, 13900139002 → Alpha
- Zhao Lei (Product Manager): zhaolei@company.com, 13900139003 → Beta, Gamma
- Zhang Wei (Backend Dev): zhangwei@company.com, 13900139004 → Beta
- Ma Qiang (Ops): maqiang@company.com, 13900139005 → Alpha
- Zhou Ming (Frontend Dev): zhouming@company.com, 13900139006 → Beta

**Strict scoring:**
- **1.0**: All 7 elements present; contact info includes email/phone; clear professional structure
- **0.6–0.8**: 5–6 elements present; structure reasonable; contact info partially present (names only)
- **0.3–0.5**: 3–4 elements; missing to-do rates, contact info, or risk annotations
- **0.0–0.2**: Report incomplete or unstructured
