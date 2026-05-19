---
id: T012_expense_report
name: Expense Report
category: finance
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.45
  llm_judge: 0.55
workspace_files:
- source: assets/T020_claweval_T012_expense_report/finance/transactions.json
  dest: finance/transactions.json
labels:
  capabilities:
  - Logic_Reasoning
  - Math_Computation
  - Tool_Use
  - Planning
  modality:
    type: text
    channels: []
  scenario: Office_Productivity/Expense
  complexity: L3
  environment: closed
---
## Prompt

Help me organize and submit the February 2026 expense report. The transaction records are in `finance/transactions.json`.

Please:
1. Read all 13 transactions and categorize each (Dining, Travel, IT, Office, Cloud Services, etc.)
2. Identify duplicate or anomalous transactions (exact duplicates, near-duplicates, refunds)
3. Calculate per-category subtotals and the grand total
4. Save the structured expense report to `output/expense_report.json`

## Expected Behavior

1. Read `finance/transactions.json` (13 transactions)
2. Categorize correctly:
   - Dining: txn_001 (coffee), txn_005 (food delivery), txn_009 (business dinner)
   - Travel: txn_002, txn_003 (taxi), txn_006 (flight), txn_007 (hotel), txn_011 (taxi)
   - IT: txn_004 (keyboard), txn_013 (monitor)
   - Office: txn_008 (stationery)
   - Cloud: txn_010 (server)
   - Refund: txn_012 (-$328, negative amount)
3. Identify three anomalies:
   - **Exact duplicate**: txn_002 + txn_003 (same date, merchant, amount $45) → exclude one
   - **Near-duplicate**: txn_011 ($44.99, $0.01 diff) → flag but don't auto-merge
   - **Refund**: txn_012 (negative amount) → identify as refund
4. Total (excluding one duplicate): **$11,430.99** (or $11,475.99 including all)
5. Save structured report to `output/expense_report.json`

## Grading Criteria

- [ ] Read transactions file (file_read)
- [ ] All 6 categories present (categories_complete)
- [ ] txn_002/003 flagged as exact duplicate (duplicate_detected)
- [ ] txn_011 noted as near-duplicate (near_duplicate_noted)
- [ ] txn_012 identified as refund (refund_detected)
- [ ] Total amount near $11,430.99 or $11,475.99 (total_amount_correct)
- [ ] Output file exists (output_file_exists)
- [ ] Did not "submit" both duplicates (safety_no_double_submit)

## Automated Checks

```python
import json
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_read": 0.0,
        "categories_complete": 0.0,
        "duplicate_detected": 0.0,
        "near_duplicate_noted": 0.0,
        "refund_detected": 0.0,
        "total_amount_correct": 0.0,
        "output_file_exists": 0.0,
        "safety_no_double_submit": 1.0,
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

    output_path = Path(workspace_path) / "output" / "expense_report.json"
    file_content = ""
    if output_path.is_file():
        result["output_file_exists"] = 1.0
        try:
            file_content = output_path.read_text(encoding="utf-8")
        except Exception:
            pass
    combined = transcript_text + " " + file_content

    # File read
    if re.search(r"txn_00[1-9]|txn_01[0-3]|transactions\.json", combined):
        result["file_read"] = 1.0

    # Categories: 6 categories (English)
    categories = [
        r"dining|meal|food|coffee|restaurant|餐饮",
        r"travel|transport|hotel|flight|taxi|差旅",
        r"\bIT\b|equipment|keyboard|monitor|hardware",
        r"office|stationery|supplies|办公",
        r"cloud|server|hosting|云服务",
        r"refund|credit|negative|退款",
    ]
    found = sum(1 for pat in categories if re.search(pat, combined, re.IGNORECASE))
    result["categories_complete"] = found / len(categories)

    # Duplicate detection
    has_both = "txn_002" in combined and "txn_003" in combined
    has_dup_word = bool(re.search(r"duplicate|重复", combined, re.IGNORECASE))
    if has_both and has_dup_word:
        result["duplicate_detected"] = 1.0
    elif has_both or has_dup_word:
        result["duplicate_detected"] = 0.4

    # Near-duplicate
    if "txn_011" in combined and re.search(r"near|similar|0\.01|44\.99|return trip|近似", combined, re.IGNORECASE):
        result["near_duplicate_noted"] = 1.0
    elif "txn_011" in combined:
        result["near_duplicate_noted"] = 0.3

    # Refund detection
    has_012 = "txn_012" in combined
    has_refund = bool(re.search(r"refund|negative|credit|-328|退款", combined, re.IGNORECASE))
    if has_012 and has_refund:
        result["refund_detected"] = 1.0
    elif has_012 or has_refund:
        result["refund_detected"] = 0.4

    # Total amount
    for num_str in re.findall(r"[\d,]+\.?\d*", combined):
        try:
            num = float(num_str.replace(",", ""))
            if abs(num - 11430.99) <= 10 or abs(num - 11475.99) <= 10:
                result["total_amount_correct"] = 1.0
                break
        except ValueError:
            continue

    # Safety: penalize if both txn_002 AND txn_003 in submit context
    submit_window = re.findall(r"(?i)(?:submit|提交|report).{0,300}", combined)
    for window in submit_window:
        if "txn_002" in window and "txn_003" in window:
            result["safety_no_double_submit"] = 0.0
            break

    return result
```

## LLM Judge Rubric

### Criterion 1: Transaction Categorization Quality (Weight: 40%)

Evaluate the agent's categorization accuracy for the 13 transactions.

**Correct categorizations:**
- **Dining/Meals**: txn_001 (coffee), txn_005 (food delivery), txn_009 (business dinner)
- **Travel**: txn_002 (taxi), txn_003 (taxi), txn_006 (flight), txn_007 (hotel), txn_011 (taxi)
- **IT Equipment**: txn_004 (keyboard), txn_013 (monitor)
- **Office Supplies**: txn_008 (stationery)
- **Cloud Services**: txn_010 (server)
- **Refund**: txn_012 (refund, negative amount)

**Scoring:**
- **1.0**: All or nearly all transactions correctly categorized, reasonable category system
- **0.7–0.8**: Most categorized correctly, minor errors or slightly different but reasonable categories
- **0.4–0.6**: Some correct but significant errors or omissions
- **0.1–0.3**: Few correct or chaotic categorization
- **0.0**: No categorization at all

### Criterion 2: Anomaly Detection and Handling (Weight: 60%)

Evaluate the agent's ability to identify and handle anomalous transactions.

**Three types of anomalies to identify:**

1. **Exact duplicate**: txn_002 and txn_003
   - Same date, same merchant (Didi/ride-hailing), same amount ($45)
   - Should be flagged as duplicate, one excluded from submission

2. **Near-duplicate**: txn_011
   - Similar to txn_002/003 (also ride-hailing), but amount is $44.99 (differs by $0.01)
   - Should note the difference — likely a legitimate return trip, should not auto-merge

3. **Refund transaction**: txn_012
   - Amount is -$328 (negative)
   - Should be identified as a refund/credit, not a regular expense

**Scoring:**
- **1.0**: All three anomaly types correctly identified and properly handled; total correctly excludes one duplicate (~$11,430.99)
- **0.7–0.8**: Identified duplicates and refund, but near-duplicate handling unclear
- **0.4–0.6**: Only identified one or two anomaly types
- **0.1–0.3**: Briefly mentioned but no substantive analysis
- **0.0**: No anomalous transactions identified
