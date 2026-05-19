---
id: CTB_A03_cashflow_risk_memo
name: Cashflow Risk Alert Memo
category: data_analysis
grading_type: hybrid
timeout_seconds: 240
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T044_claweval_CTB_A03_cashflow_risk_memo/fixtures/docs/cashflow_history.csv
  dest: fixtures/docs/cashflow_history.csv
- source: assets/T044_claweval_CTB_A03_cashflow_risk_memo/fixtures/docs/forecast_policy.md
  dest: fixtures/docs/forecast_policy.md
labels:
  complexity: L3
  environment: closed
  capabilities:
  - Tool_Use
  - Math_Computation
  - Logic_Reasoning
  scenario: Data_Analytics/Business_Intelligence
  modality:
    type: text
    channels: []
---
## Prompt

Based on the 2 attached files in `fixtures/docs/`, perform a rolling cashflow forecast and output the final memo directly.

Attachments:
- `fixtures/docs/cashflow_history.csv`
- `fixtures/docs/forecast_policy.md`

Requirements:
1. Strictly follow the methodology described in `forecast_policy.md` to produce a rolling forecast for 2026-01 through 2026-06.
2. You must provide a forecast table containing at least the following columns:
   - Month
   - Forecast Inflow
   - Forecast Outflow
   - Net Cash Flow
   - Ending Cash Balance
   - Below Safety Line (yes/no)
   - Funding Gap
3. The final memo must include:
   - Executive Summary
   - Forecast Table
   - List of Risk Months
   - Minimum Cash Balance Point and Peak Funding Gap
   - Recommended Actions
4. Recommended actions must be aligned with risk time points and cover at least:
   - Short-term financing / credit facility arrangements
   - Accelerated accounts receivable collection
5. All monetary values are in millions of CNY; do not change the methodology unless instructed.
6. Output the complete memo directly in your final reply. Do not output Python code, pseudocode, or intermediate drafts.

Note:
- This is a closed-world analysis task; you may only use data and rules from the attachments.
- Do not invent hypothetical scenarios that do not exist in the data.

## Expected Behavior

1. Read `cashflow_history.csv` and `forecast_policy.md` from `fixtures/docs/`.
2. Apply the forecast methodology:
   - For 2026-01 through 2026-06, inflow/outflow uses the **2025 same-month** values.
   - Starting cash balance = **7.4** (2025-12-31 ending balance).
   - Safety line = **5.0**.
3. Reference forecast results (ending balance per month):
   - Jan: ~6.4, Feb: ~5.5, Mar: ~4.7, Apr: ~4.1, May: ~4.2, Jun: ~4.5.
4. Risk months (below safety line): **2026-03, 2026-04, 2026-05, 2026-06**.
5. Minimum cash balance point: **2026-04 at 4.1**.
6. Peak funding gap: **2026-04 at 0.9** (5.0 - 4.1).
7. Recommendations should include at minimum:
   - Secure short-term credit / bridge financing before March.
   - Accelerate accounts receivable collection in Feb-April.

## Grading Criteria

- [ ] Starting balance 7.4 and safety line 5.0 mentioned (`starting_balance_and_safety_line`).
- [ ] At least 4 of the 6 monthly ending balances are within the expected range (`monthly_balances_correct`).
- [ ] Minimum cash point ~4.1 (in April) is identified (`minimum_point_identified`).
- [ ] Peak funding gap ~0.9 is mentioned (`peak_gap_identified`).
- [ ] LLM judge evaluates forecast-data accuracy and risk-analysis / recommendation quality.

## Automated Checks

```python
import re


_MONTH_WINDOWS = {
    "2026-01": ["2026-01", "1月", "01月", "jan", "january"],
    "2026-02": ["2026-02", "2月", "02月", "feb", "february"],
    "2026-03": ["2026-03", "3月", "03月", "mar", "march"],
    "2026-04": ["2026-04", "4月", "04月", "apr", "april"],
    "2026-05": ["2026-05", "5月", "05月", "may"],
    "2026-06": ["2026-06", "6月", "06月", "jun", "june"],
}


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "starting_balance_and_safety_line": 0.0,
        "monthly_balances_correct": 0.0,
        "minimum_point_identified": 0.0,
        "peak_gap_identified": 0.0,
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
    lower = text.lower()

    def _has_number(t, low, high):
        for match in re.finditer(r"-?\d+(?:\.\d+)?", t):
            try:
                value = float(match.group(0))
            except ValueError:
                continue
            if low <= value <= high:
                return True
        return False

    def _month_window(t, labels):
        lines = t.splitlines()
        for line in lines:
            ll = line.lower()
            if "|" in line and any(label in ll for label in labels):
                return ll
        for idx, line in enumerate(lines):
            ll = line.lower()
            if any(label in ll for label in labels):
                start = max(0, idx - 1)
                end = min(len(lines), idx + 4)
                return " ".join(lines[start:end]).lower()
        return t.lower()

    sb_score = 0.0
    if _has_number(normalized, 7.3, 7.5):
        sb_score += 0.5
    if _has_number(normalized, 4.9, 5.1) and any(
        kw in text or kw in lower for kw in ["safety line", "safety threshold", "安全线"]
    ):
        sb_score += 0.5
    result["starting_balance_and_safety_line"] = min(sb_score, 1.0)

    expected = {
        "2026-01": (6.25, 6.55),
        "2026-02": (5.35, 5.65),
        "2026-03": (4.55, 4.85),
        "2026-04": (3.95, 4.25),
        "2026-05": (4.05, 4.35),
        "2026-06": (4.35, 4.65),
    }
    months_ok = 0
    for month, (low, high) in expected.items():
        window = _month_window(normalized, _MONTH_WINDOWS[month])
        if _has_number(window, low, high):
            months_ok += 1
    result["monthly_balances_correct"] = min(months_ok / 4, 1.0)

    if _has_number(normalized, 3.95, 4.25) and any(
        kw in text or kw in lower
        for kw in ["最低", "峰值", "缺口", "2026-04", "4月",
                   "minimum", "lowest", "peak", "gap", "april", "shortfall"]
    ):
        result["minimum_point_identified"] = 1.0

    if _has_number(normalized, 0.85, 0.95):
        result["peak_gap_identified"] = 1.0

    return result
```

## LLM Judge Rubric

### Criterion 1: Forecast Data Accuracy (Weight: 57%)

Evaluate the accuracy of the cashflow forecast data.

**Ground truth:**
- Starting cash balance (2025-12-31): **7.4 million CNY**.
- Safety line: **5.0 million CNY**.
- Forecast method: use 2025 same-month values as forecast for 2026-01 to 2026-06.

**Monthly ending balances (approximate):**
- 2026-01: ~6.4M.
- 2026-02: ~5.5M.
- 2026-03: ~4.7M (below safety line).
- 2026-04: ~4.1M (minimum point, below safety line).
- 2026-05: ~4.2M (below safety line).
- 2026-06: ~4.5M (below safety line).

**Key findings:**
- Risk months: 2026-03 through 2026-06 (all below the 5.0M safety line).
- Minimum cash point: 2026-04 at ~4.1M.
- Peak funding gap: ~0.9M (in April: 5.0 - 4.1).

**Scoring bands:**
- **0.9-1.0**: All 6 monthly balances within reasonable range; correct risk months; correct minimum and gap.
- **0.7-0.8**: Most balances correct; risk months identified; minor calculation differences.
- **0.5-0.6**: Correct trend but some balance errors; partial risk identification.
- **0.3-0.4**: Only a few months correct; missing key risk identification.
- **0.0-0.2**: No meaningful forecast data.

### Criterion 2: Risk Analysis & Recommendations (Weight: 43%)

Evaluate the quality of risk analysis and action recommendations.

**Expected elements:**
1. Methodology explanation: using 2025 same-month data, seasonal pattern, safety line at 5.0M.
2. Risk month identification: March through June below safety line.
3. Minimum point: April 2026 at ~4.1M, gap ~0.9M.
4. Action recommendations aligned with the risk timeline:
   - Secure short-term credit / bridge financing before March.
   - Accelerate accounts receivable collection in Feb-April.

**Scoring bands:**
- **0.9-1.0**: Clear methodology; all risk months identified; specific timeline-aligned actions.
- **0.7-0.8**: Risk months identified; recommendations present but less specific.
- **0.5-0.6**: Some risk identification; generic recommendations.
- **0.3-0.4**: Minimal risk analysis.
- **0.0-0.2**: No meaningful analysis.
