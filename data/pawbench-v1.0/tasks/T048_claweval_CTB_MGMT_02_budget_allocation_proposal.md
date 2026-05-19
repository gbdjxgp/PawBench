---
id: CTB_MGMT_02_budget_allocation_proposal
name: Q2 Budget Allocation Proposal
category: data_analysis
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files:
- source: assets/T048_claweval_CTB_MGMT_02_budget_allocation_proposal/fixtures/finance/transactions.json
  dest: fixtures/finance/transactions.json
- source: assets/T048_claweval_CTB_MGMT_02_budget_allocation_proposal/fixtures/gmail/inbox.json
  dest: fixtures/gmail/inbox.json
labels:
  complexity: L3
  environment: closed
  capabilities:
  - Tool_Use
  - Planning
  - Math_Computation
  - Logic_Reasoning
  - Self_Verification
  scenario: Data_Analytics/Business_Intelligence
  modality:
    type: text
    channels: []
---
## Prompt

You are the company's CFO. Develop the **Q2 budget allocation plan** using the two attached files in `fixtures/`:

- `fixtures/finance/transactions.json` — Q1 actual spend rolled up by department.
- `fixtures/gmail/inbox.json` — Q2 budget requests from each department director, plus the CEO's total-budget notification and priority guidance.

Requirements:
1. Read Q1 actual spending per department from `transactions.json`.
2. Read Q2 budget requests from each department's director email, plus the CEO's total-budget email.
3. Analyze:
   - Q1 spending breakdown by department.
   - Q2 total requested amount vs. the Q2 total budget set by the CEO.
   - The CEO's stated priority order.
4. Develop the Q2 allocation plan:
   - Q2 total budget is **1,800,000 CNY** (1.8 million).
   - **Administration** and **HR** must maintain Q1 levels (combined ≈ 245,000 CNY).
   - The remaining **1,555,000 CNY** is split among **Engineering**, **Marketing**, and **Sales**.
   - Reflect Q1 execution, Q2 request justification, and the CEO's priorities.
5. Generate a budget allocation report containing:
   - Q1 spending analysis (by department).
   - Q2 allocation amount and rationale per department.
   - Verification that the total stays within the 1.8M budget.
   - Explanation for any department whose request was reduced.

Notes:
- All amounts are in CNY.
- The final response must be the report itself, not Python code or intermediate calculations.

## Expected Behavior

1. Q1 actuals (from `transactions.json`):
   - Engineering 850K, Marketing 320K, Sales 180K, Administration 150K, HR 95K → Q1 total ≈ **1,595K**.
2. Q2 requests (from gmail):
   - Engineering 950K (+11.8%), Marketing 480K (+50%), Sales 180K (flat).
   - Combined requests for Eng/Mkt/Sales = **1,610K**, which **exceeds** the available 1,555K (after fixing Admin+HR at 245K) → must trim.
3. CEO priorities (from `ceo@innovate.cn` email): (1) AI product line / Engineering, (2) Sales growth, (3) Brand building.
4. A reasonable allocation respecting all constraints:
   - **Engineering: full 950K** (CEO's #1 priority — AI strategy + mobile refactor).
   - **Sales: 180K** (CEO #2; flat request, ROI proven by Q1 over-target revenue).
   - **Marketing: 425K** (CEO #3; trimmed by ~55K from 480K request because requests exceed budget).
   - **Administration: 150K** + **HR: 95K** (fixed at Q1 levels per CEO).
   - Total = 950 + 180 + 425 + 150 + 95 = **1,800K** (within budget).
5. Report explicitly justifies the Marketing reduction, citing budget cap and CEO priority order; alternative balanced allocations are acceptable as long as they (a) honour the 1.8M cap, (b) hold Admin/HR at Q1 levels, (c) reflect the CEO priority order, and (d) explain any reductions.

## Grading Criteria

- [ ] Both data sources referenced (finance + gmail) (`sources_referenced`).
- [ ] All four key Q1 figures cited correctly: Engineering 850, Marketing 320, Sales 180, Admin 150 (`q1_data_correct`).
- [ ] Q2 total budget of 1.8M / 1,800,000 stated and respected (`budget_constraint_present`).
- [ ] At least one department reduction is named (Marketing/Sales) and justified (`reduction_acknowledged`).
- [ ] CEO priorities reflected: Engineering favoured, Marketing trimmed (`ceo_priorities_followed`).
- [ ] Output uses a Markdown table (`table_structure_present`).
- [ ] LLM judge evaluates Q1 analysis accuracy and Q2 allocation rationale.

## Automated Checks

```python
import re


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "sources_referenced": 0.0,
        "q1_data_correct": 0.0,
        "budget_constraint_present": 0.0,
        "reduction_acknowledged": 0.0,
        "ceo_priorities_followed": 0.0,
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
    lower = text.lower()
    clean = text.replace(",", "").replace("，", "").replace(" ", "")

    # sources_referenced
    fin_seen = bool(re.search(r"transactions\.json|finance|q1.*actual|q1.*spend", lower))
    mail_seen = bool(re.search(r"inbox\.json|gmail|email|ceo.*notif|director.*request", lower))
    result["sources_referenced"] = 0.5 * float(fin_seen) + 0.5 * float(mail_seen)

    # q1_data_correct — engineer 850, marketing 320, sales 180, admin 150
    pairs = [
        ("engineer", ["850000", "850"]),
        ("market",   ["320000", "320"]),
        ("sales",    ["180000", "180"]),
        ("admin",    ["150000", "150"]),
    ]
    found = sum(
        1 for dept, vals in pairs
        if dept in lower and any(v in clean for v in vals)
    )
    result["q1_data_correct"] = min(found / 3, 1.0)

    # budget_constraint_present — 1,800,000 / 1.8M / 180万
    if (re.search(r"1[,\s]*8(?:00)?[,\s]*000", text)
            or re.search(r"1\.8\s*[Mm]|1\.8\s*million|180\s*万", text)
            or "1800000" in clean):
        if any(kw in lower for kw in ["budget", "total", "allocation", "cap", "ceiling"]):
            result["budget_constraint_present"] = 1.0
        else:
            result["budget_constraint_present"] = 0.5

    # reduction_acknowledged — explicit cut/reduce of marketing or sales (or any dept)
    if re.search(r"(reduc|cut|trim|lower|降低|削减|缩减).{0,40}(market|mkt|sales|department|dept)", lower):
        result["reduction_acknowledged"] = 1.0
    elif any(kw in lower for kw in ["exceed", "shortfall", "over budget", "超出", "超过"]):
        result["reduction_acknowledged"] = 0.5

    # ceo_priorities_followed — engineering favoured AND marketing trimmed
    eng_favoured = bool(re.search(
        r"engineer.{0,80}(?:priorit|full|ai|strateg|first|highest|top|top.priorit)",
        lower, re.DOTALL,
    ))
    mkt_trimmed = bool(re.search(
        r"market.{0,80}(?:reduc|cut|trim|lower|adjust|brand|third|lowest)",
        lower, re.DOTALL,
    ))
    result["ceo_priorities_followed"] = 0.5 * float(eng_favoured) + 0.5 * float(mkt_trimmed)

    # table_structure_present
    if "|" in text and "---" in text:
        result["table_structure_present"] = 1.0

    return result
```

## LLM Judge Rubric

### Criterion 1: Q1 Spending Analysis Accuracy (Weight: 46%)

Evaluate the accuracy of Q1 spending analysis.

**Ground truth — Q1 actual spend:**
- Engineering: 850,000 CNY
- Marketing: 320,000 CNY
- Sales: 180,000 CNY
- Administration: 150,000 CNY
- HR: 95,000 CNY
- Total Q1 actual: ≈ 1,595,000 CNY

**Scoring bands:**
- **0.9–1.0**: All department Q1 figures correct; total calculated.
- **0.7–0.8**: Most departments correct; total approximately right.
- **0.5–0.6**: Some figures correct.
- **0.3–0.4**: Minimal Q1 data.
- **0.0–0.2**: No Q1 analysis.

### Criterion 2: Q2 Allocation Rationale & Plan (Weight: 54%)

Evaluate the quality of the Q2 allocation rationale and plan.

**Ground truth:**
- Q2 total budget: 1,800,000 CNY.
- Administration + HR fixed at Q1 levels (≈ 245K combined).
- Remaining 1,555K split among Engineering, Marketing, Sales.
- CEO priority order: (1) AI/Engineering full request; (2) Sales support; (3) Brand/Marketing.
- Total Q2 requests (Eng 950 + Mkt 480 + Sales 180 = 1,610K) exceed the 1,555K available — Marketing or Sales must be cut.
- Cuts must be explained with explicit justification.

**Scoring bands:**
- **0.9–1.0**: Budget constraint respected; CEO priorities reflected; clear reduction rationale; complete per-department allocation.
- **0.7–0.8**: Budget mostly balanced; priorities mentioned; some justification.
- **0.5–0.6**: Budget acknowledged; partial allocation plan.
- **0.3–0.4**: Mentions budget but incomplete plan.
- **0.0–0.2**: No allocation plan.
