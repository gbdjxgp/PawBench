---
id: CTB_DATA_20_project_cost_vs_plan
name: Project Cost vs Plan Comparison
category: data_analysis
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files:
- source: assets/T047_claweval_CTB_DATA_20_project_cost_vs_plan/fixtures/finance/transactions.json
  dest: fixtures/finance/transactions.json
- source: assets/T047_claweval_CTB_DATA_20_project_cost_vs_plan/fixtures/todo/tasks.json
  dest: fixtures/todo/tasks.json
labels:
  complexity: L3
  environment: closed
  capabilities:
  - Tool_Use
  - Math_Computation
  - Planning
  - Logic_Reasoning
  scenario: Data_Analytics/Business_Intelligence
  modality:
    type: text
    channels: []
---
## Prompt

Please compare the **Smart Campus** project's actual expenditures against its planned budget. The data has been pre-fetched and is available in two attachments:

- `fixtures/finance/transactions.json` — list of finance transactions (each has `description`, `amount`, `date`, `category`, `department`).
- `fixtures/todo/tasks.json` — list of project tasks (each has `title`, `description` containing the planned budget, `status`, `due_date`, `assignee`).

Filter to **Smart Campus**-related rows only (ignore Data Platform / other projects).

Requirements:
1. Map each finance transaction to the corresponding project stage by reading the transaction `description`. Stages: Requirements Analysis, UI Design, Front-end Development, Back-end Development, Testing, Deployment & Go-live, Documentation Delivery.
2. For every stage, extract the **planned budget** from the matching todo task's `description` (e.g. "budget 120K" → 120,000 CNY).
3. For every stage, compute **actual spend** by summing matching transactions, and compute the variance (`actual − planned`).
4. Compute the **total planned**, **total actual**, and **overall overrun** (both in absolute amount and as a percentage of planned).
5. Track project progress: list which stages are `completed`, `in_progress`, and `pending`.
6. Assess the **budget risk** — is the project on track, at risk, or already over? Identify which stages are the largest cost drivers.
7. Output a single Markdown report with: a stage-by-stage variance table, totals, progress summary, risk assessment, and concrete recommendations.

Notes:
- All amounts are in CNY.
- "Variance" = actual − planned (positive = over budget).
- The final response must be the report itself, not Python code or intermediate calculations.

## Expected Behavior

1. Filter both files to Smart Campus rows.
2. Per-stage variance:
   - Requirements Analysis: planned 50K, actual 0 (no transaction yet — task already completed but no spend recorded).
   - UI Design: planned 80K, actual 80K → 0 (on budget).
   - Front-end Development: planned 120K, actual 150K → **+30K** (overspent).
   - Back-end Development: planned 180K, actual 200K → **+20K** (overspent).
   - Testing: planned 30K, actual 35K → +5K.
   - Deployment & Go-live: planned 50K, actual 60K → +10K.
   - Documentation Delivery: planned 20K, actual 25K → +5K.
3. Totals (counting only stages with actual spend, matching the upstream ground truth): planned **530K**, actual **550K**, overrun **+20K (≈ +3.8%)**.
4. Progress: completed 3 (Requirements Analysis, UI Design, Front-end), in_progress 3 (Back-end, Testing, Documentation), pending 1 (Deployment).
5. Risk assessment: project is over budget by ~3.8%; the largest drivers are Front-end (+30K) and Back-end (+20K) outsourcing; Deployment and Documentation are still in progress so the gap could widen.

## Grading Criteria

- [ ] Both data files are referenced and Smart Campus filtering is applied (`api_calls_referenced`).
- [ ] Total actual `550K` and total planned `530K` both stated (`totals_correct`).
- [ ] Overall overrun stated as `+3.8%` (or `~3.8%`) and `20K` (`overrun_correct`).
- [ ] Front-end (120 → 150) and Back-end (180 → 200) overruns explicitly called out (`key_stages_correct`).
- [ ] Progress statuses (`completed` / `in_progress` / `pending`) are tracked in the report (`progress_statuses_present`).
- [ ] Output uses a Markdown table (`table_structure_present`).
- [ ] LLM judge evaluates stage-by-stage accuracy, progress tracking, and risk-assessment quality.

## Automated Checks

```python
import re


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "api_calls_referenced": 0.0,
        "totals_correct": 0.0,
        "overrun_correct": 0.0,
        "key_stages_correct": 0.0,
        "progress_statuses_present": 0.0,
        "table_structure_present": 0.0,
    }

    def _all_assistant_text(msgs):
        parts = []
        for m in msgs:
            actual = m.get("message", m)
            if actual.get("role") != "assistant":
                continue
            content = actual.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        parts.append(block.get("text", ""))
        return " ".join(parts)

    def _last_assistant_text(msgs):
        for m in reversed(msgs):
            actual = m.get("message", m)
            if actual.get("role") != "assistant":
                continue
            content = actual.get("content", "")
            if isinstance(content, str) and content.strip():
                return content
            if isinstance(content, list):
                buf = [b.get("text", "") for b in content if isinstance(b, dict)]
                joined = " ".join(buf).strip()
                if joined:
                    return joined
        return ""

    text = _last_assistant_text(transcript)
    if len(text) < 200:
        text = _all_assistant_text(transcript)
    lowered = text.lower()
    clean = (
        text.replace(",", "").replace("，", "")
        .replace("¥", "").replace("￥", "")
        .replace("CNY", "").replace("cny", "")
    )

    def has_bounded(t, num):
        return bool(re.search(rf"(?<!\d){re.escape(num)}(?!\d)", t))

    # api_calls_referenced — both data sources mentioned by name/path.
    fin_seen = bool(re.search(r"transactions\.json|finance|transaction", lowered))
    todo_seen = bool(re.search(r"tasks\.json|todo|task list|milestone", lowered))
    result["api_calls_referenced"] = float(fin_seen) * 0.5 + float(todo_seen) * 0.5

    # totals_correct — total actual 550K and total planned 530K.
    if has_bounded(clean, "550000") or re.search(r"550\s*[Kk万]|550\.0", text):
        result["totals_correct"] += 0.5
    if has_bounded(clean, "530000") or re.search(r"530\s*[Kk万]|530\.0", text):
        result["totals_correct"] += 0.5

    # overrun_correct — 3.8% AND 20K mentioned with "over"/"variance"/"超".
    pct_ok = bool(re.search(r"3\.8\s*%|3\.77\s*%|3\.78\s*%", clean))
    abs_ok = (
        any(kw in lowered for kw in ["overrun", "over budget", "overspent", "variance", "超支", "超预算"])
        and (has_bounded(clean, "20000") or re.search(r"\b20\s*[Kk]", text) or re.search(r"\+\s*20\b", text))
    )
    if pct_ok and abs_ok:
        result["overrun_correct"] = 1.0
    elif pct_ok or abs_ok:
        result["overrun_correct"] = 0.5

    # key_stages_correct — front-end 120→150, back-end 180→200.
    front = (("front" in lowered or "前端" in text)
             and has_bounded(clean, "150") and has_bounded(clean, "120"))
    back = (("back" in lowered or "后端" in text)
            and has_bounded(clean, "200") and has_bounded(clean, "180"))
    result["key_stages_correct"] = 0.5 * float(front) + 0.5 * float(back)

    # progress_statuses_present — at least 2 distinct status labels.
    statuses = ["completed", "in progress", "in_progress", "pending",
                "已完成", "进行中", "待开始", "未开始"]
    found = sum(1 for s in statuses if s in lowered)
    result["progress_statuses_present"] = min(found / 2, 1.0)

    # table_structure_present
    if "|" in text and "---" in text:
        result["table_structure_present"] = 1.0

    return result
```

## LLM Judge Rubric

### Criterion 1: Stage-by-stage Accuracy (Weight: 46%)

Evaluate the accuracy of stage-by-stage cost comparison.

**Ground truth — Budget vs Actual by stage (Smart Campus only):**

| Stage | Budget (K) | Actual (K) | Variance |
|-------|-----------|-----------|----------|
| Requirements Analysis | 50 | 0 (no transaction) | — |
| UI Design | 80 | 80 | 0 (on budget) |
| Front-end Development | 120 | 150 | +30K (overspent) |
| Back-end Development | 180 | 200 | +20K (overspent) |
| Testing | 30 | 35 | +5K |
| Deployment & Go-live | 50 | 60 | +10K |
| Documentation Delivery | 20 | 25 | +5K |

Key insight: Front-end (+30K) and Back-end (+20K) are the biggest overruns.

**Scoring bands:**
- **0.9–1.0**: All stages with correct budget / actual / variance values; biggest overruns explicitly identified.
- **0.7–0.8**: Most stages correct; key overruns identified.
- **0.5–0.6**: 3–4 stages with partial data; some variance calculations.
- **0.3–0.4**: Minimal stage comparison.
- **0.0–0.2**: No meaningful stage data.

### Criterion 2: Progress Tracking (Weight: 31%)

Evaluate the accuracy of project task progress tracking.

**Ground truth:**
- Completed (3): Requirements Analysis, UI Design, Front-end Development.
- In progress (3): Back-end Development, Testing, Documentation Delivery.
- Pending (1): Deployment & Go-live.

**Scoring bands:**
- **0.9–1.0**: All stages tagged with the correct status; counts match.
- **0.7–0.8**: Most stages with correct status; minor misclassifications.
- **0.5–0.6**: Partial status coverage; some stages missing.
- **0.3–0.4**: Minimal progress tracking.
- **0.0–0.2**: No meaningful progress data.

### Criterion 3: Risk Assessment & Recommendations (Weight: 23%)

Evaluate the quality of budget-risk assessment and concrete recommendations.

**Ground truth:**
- Total overrun: +20K, ≈ +3.8% over budget.
- Project is currently within an acceptable range but trending over budget.
- Front-end and Back-end outsourcing are the primary cost drivers.
- Remaining items (Deployment, Documentation) are still in progress — risk of further overrun.
- Need to monitor closely to prevent budget blow-out and consider contingency reserves.

**Scoring bands:**
- **0.9–1.0**: Identifies 3.8% overrun; clear risk items with specific, actionable recommendations.
- **0.7–0.8**: Overrun calculated; some risk discussion and suggestions.
- **0.5–0.6**: Overrun approximately noted; basic risk mention.
- **0.3–0.4**: Minimal risk assessment.
- **0.0–0.2**: No meaningful risk analysis.
