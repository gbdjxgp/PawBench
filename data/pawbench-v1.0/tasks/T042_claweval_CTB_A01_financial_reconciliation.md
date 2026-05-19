---
id: CTB_A01_financial_reconciliation
name: Financial Reconciliation Analysis
category: data_analysis
grading_type: hybrid
timeout_seconds: 240
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files:
- source: assets/T042_claweval_CTB_A01_financial_reconciliation/fixtures/docs/crm_export.csv
  dest: fixtures/docs/crm_export.csv
- source: assets/T042_claweval_CTB_A01_financial_reconciliation/fixtures/docs/bank_settlements.csv
  dest: fixtures/docs/bank_settlements.csv
- source: assets/T042_claweval_CTB_A01_financial_reconciliation/fixtures/docs/invoice_ledger.csv
  dest: fixtures/docs/invoice_ledger.csv
labels:
  complexity: L3
  environment: closed
  capabilities:
  - Tool_Use
  - Logic_Reasoning
  - Math_Computation
  - Self_Verification
  scenario: Data_Analytics/Business_Intelligence
  modality:
    type: text
---
## Prompt

Complete a month-end sales reconciliation using the 3 attached files in `fixtures/docs/`, and produce a structured reconciliation report.

Attachments:
- `fixtures/docs/crm_export.csv`
- `fixtures/docs/bank_settlements.csv`
- `fixtures/docs/invoice_ledger.csv`

Requirements:
1. Perform a three-way reconciliation using transaction ID as the primary key:
   - CRM: `transaction_id`
   - Bank settlements: `external_ref`
   - Invoice ledger: `invoice_ref`
2. Classify each record into one of these categories:
   - Full match
   - Amount discrepancy
   - Missing bank entry
   - Missing invoice
   - Bank-only (unmatched)
3. Your output must include:
   - Summary: count of full matches, count of exceptions, total impact amount
   - Detail table: for each exception, list transaction ID, discrepancy type, CRM amount, bank amount, invoice amount, variance, probable cause
   - Recommended actions: prioritized next steps
4. Write the report in a format suitable for sending directly to the finance lead.
5. Do not fabricate data that does not exist in the attachments.
6. Output the final reconciliation report directly — do not output Python code, pseudocode, CSV reproductions, or intermediate calculations.
7. The final response must be the complete report itself, not just an analysis plan.

Notes:
- All amounts are in CNY.
- "Total impact amount" is the sum of absolute variance amounts across all exceptions.

## Expected Behavior

1. Read all three CSVs from `fixtures/docs/`.
2. Identify the matches and exceptions:
   - **Full matches (2)**: TX-1001, TX-1006.
   - **Exceptions (5)**:
     - TX-1002: amount discrepancy — CRM/bank 980.00, invoice 890.00, variance 90.
     - TX-1003: missing bank entry — CRM/invoice 1499.00, no bank record, variance 1499.
     - TX-1004: missing invoice — CRM/bank 730.00, no invoice, variance 730.
     - TX-1005: amount discrepancy — CRM/invoice 2200.00, bank 2150.00, variance 50 (reserve/holdback).
     - UNMAPPED-7781: orphan bank entry — bank-only 560.00, no CRM match.
3. Total impact amount: **2929.00**.
4. Provide one prioritized recommendation per exception, e.g.:
   - TX-1002 → verify invoice amount (890 vs 980), likely billing error.
   - TX-1003 → trace missing bank settlement for 1,499.
   - TX-1004 → issue or locate missing invoice for 730.
   - TX-1005 → investigate 50 holdback/reserve difference.
   - UNMAPPED-7781 → identify the source of the orphan bank entry (560).

## Grading Criteria

- [ ] All five exception transaction IDs (TX-1002 / TX-1003 / TX-1004 / TX-1005 / UNMAPPED-7781) are mentioned (`tx_ids_mentioned`).
- [ ] At least 5 of the 7 key amounts (980, 890, 1499, 730, 2200, 2150, 560) appear in the report (`key_amounts_present`).
- [ ] Total impact amount 2929 is stated (`total_impact_correct`).
- [ ] Summary states "matched=2" and "exceptions=5" (`summary_counts_correct`).
- [ ] Output uses a Markdown table (`table_structure_present`).
- [ ] LLM judge evaluates exception categorization, recommendation quality, and overall report structure.

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "tx_ids_mentioned": 0.0,
        "key_amounts_present": 0.0,
        "total_impact_correct": 0.0,
        "summary_counts_correct": 0.0,
        "table_structure_present": 0.0,
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
    compact = (
        text.replace(",", "").replace("，", "")
        .replace("￥", "").replace("¥", "")
        .replace("cny", "").replace("CNY", "")
    )

    ids = ["TX-1002", "TX-1003", "TX-1004", "TX-1005", "UNMAPPED-7781"]
    found_ids = sum(1 for tx in ids if tx in text or tx.lower() in text.lower())
    result["tx_ids_mentioned"] = min(found_ids / 4, 1.0)

    amounts = ["980", "890", "1499", "730", "2200", "2150", "560"]
    def _has_bounded(t: str, num: str) -> bool:
        return bool(re.search(rf'(?<!\d){re.escape(num)}(?!\d)', t))
    found_amt = sum(1 for a in amounts if _has_bounded(compact, a))
    result["key_amounts_present"] = min(found_amt / 5, 1.0)

    if re.search(r"\b2929(?:\.0+)?\b", compact):
        result["total_impact_correct"] = 1.0

    summary_score = 0.0
    # Allow up to 80 chars between the keyword and the count so markdown table
    # cells like "| **Full matches** (all three systems agree) | **2** |" still
    # match. Use re.DOTALL so the window can span newlines (some agents put the
    # number on the next row of a table).
    if re.search(
        r"(?:full match|完全匹配|matched|reconciled cleanly).{0,80}?(?<!\d)2(?!\d)",
        text, re.IGNORECASE | re.DOTALL,
    ):
        summary_score += 0.5
    if re.search(
        r"(?:exception|异常|discrepanc|require.{0,20}attention).{0,80}?(?<!\d)5(?!\d)",
        text, re.IGNORECASE | re.DOTALL,
    ):
        summary_score += 0.5
    result["summary_counts_correct"] = min(summary_score, 1.0)

    if "|" in text and "---" in text:
        result["table_structure_present"] = 1.0

    return result
```

## LLM Judge Rubric

### Criterion 1: Exception Categorization (Weight: 38%)

Evaluate whether each of the 5 exceptions is correctly **categorized** with the right type and amounts.

**Ground truth — 5 exceptions:**
1. TX-1002 → "amount discrepancy" — CRM/bank 980, invoice 890, difference 90.
2. TX-1003 → "missing bank entry" — CRM/invoice 1499, no bank record.
3. TX-1004 → "missing invoice" — CRM/bank 730, no invoice.
4. TX-1005 → "amount discrepancy" — CRM/invoice 2200, bank 2150, difference 50 (reserve/holdback).
5. UNMAPPED-7781 → "orphan bank entry" — bank-only 560, no CRM match.

**Scoring bands:**
- **0.9–1.0**: All 5 correctly categorized with amounts and types.
- **0.7–0.8**: 4–5 identified, most types correct.
- **0.5–0.6**: 3–4 identified, some type confusion.
- **0.3–0.4**: Only 1–2 identified.
- **0.0–0.2**: No meaningful categorization.

### Criterion 2: Recommendation Quality (Weight: 31%)

Evaluate the quality and specificity of action recommendations.

**Expected recommendations (one per exception):**
- TX-1002 → verify invoice amount (890 vs 980), likely billing error.
- TX-1003 → trace missing bank settlement for 1,499.
- TX-1004 → issue or locate missing invoice for 730.
- TX-1005 → investigate 50 holdback/reserve difference.
- UNMAPPED-7781 → identify source of orphan bank entry (560).

**Scoring bands:**
- **0.9–1.0**: All 5 exceptions have specific, actionable recommendations with priority.
- **0.7–0.8**: Most exceptions have recommendations, some generic.
- **0.5–0.6**: Generic recommendations, not per-exception.
- **0.3–0.4**: Minimal recommendations.
- **0.0–0.2**: No recommendations.

### Criterion 3: Report Structure & Clarity (Weight: 31%)

Evaluate the overall report structure and clarity.

**Expected structure:**
1. Summary overview: matched count (2), exception count (5), total impact (2929).
2. Exception detail table with columns: TX ID, type, CRM/bank/invoice amounts, variance, cause.
3. Action section with prioritized recommendations.

**Scoring bands:**
- **0.9–1.0**: All 3 sections present; professional tone suitable for a finance director.
- **0.7–0.8**: Has structure but gaps in one section.
- **0.5–0.6**: Partial structure, disorganized.
- **0.3–0.4**: Minimal structure.
- **0.0–0.2**: No coherent report.
