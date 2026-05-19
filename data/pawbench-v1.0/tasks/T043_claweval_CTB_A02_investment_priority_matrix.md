---
id: CTB_A02_investment_priority_matrix
name: Project Investment Priority Matrix
category: data_analysis
grading_type: hybrid
timeout_seconds: 240
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T043_claweval_CTB_A02_investment_priority_matrix/fixtures/docs/project_a_forecast.csv
  dest: fixtures/docs/project_a_forecast.csv
- source: assets/T043_claweval_CTB_A02_investment_priority_matrix/fixtures/docs/project_b_forecast.csv
  dest: fixtures/docs/project_b_forecast.csv
- source: assets/T043_claweval_CTB_A02_investment_priority_matrix/fixtures/docs/project_c_forecast.csv
  dest: fixtures/docs/project_c_forecast.csv
- source: assets/T043_claweval_CTB_A02_investment_priority_matrix/fixtures/docs/risk_brief.md
  dest: fixtures/docs/risk_brief.md
labels:
  complexity: L3
  environment: closed
  capabilities:
  - Math_Computation
  - Logic_Reasoning
  - Tool_Use
  scenario: Data_Analytics/Business_Intelligence
  modality:
    type: text
---
## Prompt

Please complete an investment priority assessment based on the 4 attachments in `fixtures/docs/` and produce the final report in English.

Attachments:
- `fixtures/docs/project_a_forecast.csv`
- `fixtures/docs/project_b_forecast.csv`
- `fixtures/docs/project_c_forecast.csv`
- `fixtures/docs/risk_brief.md`

Requirements:
1. For each of the three projects, calculate:
   - 5-year NPV (discount rate fixed at 8%)
   - IRR
   - Dynamic payback period
2. Based on `risk_brief.md`, classify each project's risk level as:
   - High
   - Medium
   - Low
3. Scoring rules are fixed as:
   - Financial score = `NPV ranking 50% + IRR ranking 30% + Payback ranking 20%`
   - Ranking mapping: Best = 100, Middle = 70, Worst = 40
   - Risk score mapping: Low = 100, Medium = 70, High = 40
   - Composite score = `Financial score * 0.6 + Risk score * 0.4`
4. Rounding rules:
   - NPV rounded to 2 decimal places
   - IRR rounded to 2 decimal places (percentage)
   - Dynamic payback period rounded to 2 decimal places
   - Composite score rounded to 1 decimal place
5. Output must include:
   - Executive summary
   - A comparison table: Project, NPV, IRR, Payback, Risk Level, Financial Score, Risk Score, Composite Score, Priority
   - A risk-return decision matrix (table or text matrix)
   - Clearly state: Primary choice, Alternate choice, Deferred project
   - Recommendation rationale and key risk warnings
6. The final response must be the complete report itself, not Python code, pseudocode, or intermediate drafts.

Hints:
- `year=0` in `project_*_forecast.csv` represents the initial investment (negative value).
- Annual cash flow units are in million CNY.

## Expected Behavior

1. Read all four attachment files from `fixtures/docs/`.
2. Compute NPV (8% discount rate), IRR, and dynamic payback period for each project. Reference values:
   - **Project A**: NPV ≈ 1888.34, IRR ≈ 22.85%, payback ≈ 2.81, risk = Medium.
   - **Project B**: NPV ≈ 3583.23, IRR ≈ 30.02%, payback ≈ 2.43, risk = High.
   - **Project C**: NPV ≈ 2586.15, IRR ≈ 26.07%, payback ≈ 2.63, risk = Low.
3. Apply the scoring formula:
   - Financial score: B = 100, C = 70, A = 40.
   - Risk score: C = 100, A = 70, B = 40.
   - Composite: **C = 82.0, B = 76.0, A = 52.0**.
4. Final recommendation: **Primary = Project C**, **Alternate = Project B**, **Deferred = Project A**.
5. Include a risk-return decision matrix and a comparison table in the report.

## Grading Criteria

- [ ] All three project labels (Project A / B / C) appear (`projects_mentioned`).
- [ ] Each composite score (82.0, 76.0, 52.0) is present (`composite_scores_present`).
- [ ] Priority order is correct: C = primary, B = alternate, A = deferred (`priority_order_correct`).
- [ ] LLM judge evaluates financial-data accuracy (NPV/IRR/payback/risk) and methodology + recommendation quality.

## Automated Checks

```python
import re


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "projects_mentioned": 0.0,
        "composite_scores_present": 0.0,
        "priority_order_correct": 0.0,
    }

    def _all_assistant_text(msgs: list) -> str:
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

    def _last_assistant_text(msgs: list) -> str:
        for m in reversed(msgs):
            actual = m.get("message", m)
            if actual.get("role") != "assistant":
                continue
            content = actual.get("content", "")
            if isinstance(content, str) and content.strip():
                return content
            if isinstance(content, list):
                buf = []
                for block in content:
                    if isinstance(block, dict):
                        buf.append(block.get("text", ""))
                joined = " ".join(buf).strip()
                if joined:
                    return joined
        return ""

    final_text = _last_assistant_text(transcript)
    fallback_text = _all_assistant_text(transcript)
    text = final_text if len(final_text) >= 200 else fallback_text
    normalized = text.replace(",", "")
    lowered = normalized.lower()

    def _has_project(letter: str) -> bool:
        return f"project {letter}" in lowered or f"project{letter}" in lowered

    def _has_num_in_range(low: float, high: float) -> bool:
        for match in re.finditer(r"-?\d+(?:\.\d+)?", normalized):
            try:
                v = float(match.group(0))
            except ValueError:
                continue
            if low <= v <= high:
                return True
        return False

    projs = sum(1 for ch in ["a", "b", "c"] if _has_project(ch))
    result["projects_mentioned"] = min(projs / 3, 1.0)

    composite_score = 0.0
    if _has_num_in_range(81.5, 82.5):
        composite_score += 1 / 3
    if _has_num_in_range(75.5, 76.5):
        composite_score += 1 / 3
    if _has_num_in_range(51.5, 52.5):
        composite_score += 1 / 3
    result["composite_scores_present"] = min(composite_score, 1.0)

    priority_score = 0.0
    if _has_project("c") and any(kw in lowered for kw in ["primary", "priority 1", "first choice", "top priority"]):
        priority_score += 1 / 3
    if _has_project("b") and any(kw in lowered for kw in ["alternate", "priority 2", "second choice"]):
        priority_score += 1 / 3
    if _has_project("a") and any(kw in lowered for kw in ["defer", "priority 3", "lowest", "third"]):
        priority_score += 1 / 3
    result["priority_order_correct"] = min(priority_score, 1.0)

    return result
```

## LLM Judge Rubric

### Criterion 1: Financial Data Accuracy (Weight: 50%)

Evaluate the accuracy of financial calculations for all three projects.

**Ground truth:**

#### Project A
- NPV (8%): ~1888.34 million CNY
- IRR: ~22.85%
- Dynamic payback period: ~2.81 years
- Risk level: Medium

#### Project B
- NPV (8%): ~3583.23 million CNY
- IRR: ~30.02%
- Dynamic payback period: ~2.43 years
- Risk level: High

#### Project C
- NPV (8%): ~2586.15 million CNY
- IRR: ~26.07%
- Dynamic payback period: ~2.63 years
- Risk level: Low

#### Composite scores
- Financial score ranking: B (100) > C (70) > A (40).
- Risk score: C (100, low) > A (70, medium) > B (40, high).
- Final composite: **C = 82.0, B = 76.0, A = 52.0**.

**Scoring bands:**
- **0.9–1.0**: All 3 projects with correct NPV, IRR, payback, risk level, and composite scores.
- **0.7–0.8**: Most calculations correct, 1–2 minor numerical differences.
- **0.5–0.6**: Correct direction but significant calculation errors.
- **0.3–0.4**: Only 1–2 projects with partial data.
- **0.0–0.2**: No meaningful financial analysis.

**Notes:** Accept reasonable rounding differences (NPV within 50, IRR within 1%, payback within 0.1).

### Criterion 2: Methodology & Recommendation Quality (Weight: 50%)

Evaluate the quality of the investment methodology and the final recommendation.

**Expected methodology:**
- Formula: `financial_score × 0.6 + risk_score × 0.4`.
- Financial ranking: NPV 50% + IRR 30% + payback 20%, mapped to 100 / 70 / 40.
- Risk mapping: Low = 100, Medium = 70, High = 40.

**Expected recommendation:**
- Priority 1 (Primary choice): **Project C** (highest composite 82.0, low risk).
- Priority 2 (Alternate choice): **Project B** (strong financials but high risk).
- Priority 3 (Deferred): **Project A** (lowest composite 52.0).

**Scoring bands:**
- **0.9–1.0**: Methodology clearly explained; risk-return matrix present; correct priority ranking with rationale.
- **0.7–0.8**: Correct ranking with some methodology explanation.
- **0.5–0.6**: Correct ranking but thin rationale.
- **0.3–0.4**: Partial ranking or wrong priority order.
- **0.0–0.2**: No meaningful recommendation.
