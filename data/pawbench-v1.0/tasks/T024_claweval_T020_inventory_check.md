---
id: T020_inventory_check
name: Inventory Check
category: operations
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.55
  llm_judge: 0.45
workspace_files:
- source: assets/T024_claweval_T020_inventory_check/inventory/products.json
  dest: inventory/products.json
labels:
  capabilities:
  - Tool_Use
  - Planning
  - Math_Computation
  - Logic_Reasoning
  modality:
    type: text
    channels: []
  scenario: Office_Productivity/Task_Management
  complexity: L3
  environment: closed
---
## Prompt

Check inventory for items that need restocking and place reorder.

The inventory data is in `inventory/products.json`. Please:

1. Check all product stock levels
2. Identify items needing restock (below threshold)
3. **Pay special attention to "non-obvious" low stock**: stock numbers may look adequate but be insufficient relative to threshold/daily-sales/lead-time (e.g., a 4K monitor with 50 units that only covers 3 days)
4. **Note backordered items** (stock 0 + ETA passed)
5. Rank by urgency (days remaining = stock / daily_sales)
6. Recommend reasonable reorder quantities (formula: daily_sales × lead_time + (threshold − stock))
7. Save the analysis to `output/restock_plan.json`

## Expected Behavior

7 items need restock (urgency order):

1. **SKU-004** (Smart Watch S3): 0 / 15, out of stock → reorder ~45
2. **SKU-010** (USB-C Hub): 0 / 20, **backordered**, ETA 2026-03-10 has passed → reorder ~76, flag special status
3. **SKU-001** (Wireless Bluetooth Earbuds Pro): 3 / 20, ~0.4 days → reorder ~73
4. **SKU-008** (Ergonomic Mouse): 5 / 20, ~0.8 days → reorder ~45
5. **SKU-006** (Mechanical Keyboard): 8 / 25, ~2 days → reorder ~45
6. **SKU-003** (Laptop Stand): 12 / 30, ~2.4 days → reorder ~43
7. **SKU-009** (4K Monitor): 50 / 100, looks fine but daily_sales=15, lead_time=14 → only 3.3 days → reorder ~260

Output format:
```json
{
  "restock_orders": [
    {"sku": "SKU-004", "quantity": 45, "urgency": 1, "days_remaining": 0, "reason": "..."},
    ...
  ],
  "non_obvious_items": ["SKU-009"],
  "backordered_items": [{"sku": "SKU-010", "eta_passed": true}]
}
```

## Grading Criteria

- [ ] Read products file (file_read)
- [ ] At least 5 of 7 low-stock items identified (low_stock_identified)
- [ ] SKU-009 (4K Monitor) flagged as non-obvious low stock (sku009_non_obvious)
- [ ] SKU-010 (USB-C Hub) flagged as backordered with ETA past (sku010_backorder)
- [ ] At least one reorder recommendation with quantity (reorder_recommended)
- [ ] Output file exists (output_file_exists)
- [ ] No invalid SKUs ordered (safety_no_wrong_order)

## Automated Checks

```python
import json
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_read": 0.0,
        "low_stock_identified": 0.0,
        "sku009_non_obvious": 0.0,
        "sku010_backorder": 0.0,
        "reorder_recommended": 0.0,
        "output_file_exists": 0.0,
        "safety_no_wrong_order": 1.0,
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

    output_path = Path(workspace_path) / "output" / "restock_plan.json"
    file_content = ""
    payload = None
    if output_path.is_file():
        result["output_file_exists"] = 1.0
        try:
            file_content = output_path.read_text(encoding="utf-8")
            payload = json.loads(file_content)
        except Exception:
            pass
    combined = transcript_text + " " + file_content

    if re.search(r"SKU-00\d|SKU-010|products\.json", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    target_skus = ["SKU-004", "SKU-001", "SKU-008", "SKU-006", "SKU-003", "SKU-009", "SKU-010"]
    found = sum(1 for s in target_skus if s in combined)
    result["low_stock_identified"] = found / len(target_skus)

    if "SKU-009" in combined or "4K" in combined:
        if re.search(r"non.?obvious|3\.3|hidden|deceptive|safety.?line|looks adequate|actually below", combined, re.IGNORECASE):
            result["sku009_non_obvious"] = 1.0
        else:
            result["sku009_non_obvious"] = 0.4

    if "SKU-010" in combined or re.search(r"USB-?C.?[Hh]ub", combined):
        if re.search(r"backorder|ETA|2026-03-10|overdue|past|passed", combined, re.IGNORECASE):
            result["sku010_backorder"] = 1.0
        else:
            result["sku010_backorder"] = 0.4

    has_qty = bool(re.search(r"(?:quantity|qty|reorder|order).*?\d{2,4}", combined, re.IGNORECASE))
    if isinstance(payload, dict) and payload.get("restock_orders"):
        result["reorder_recommended"] = 1.0
    elif has_qty:
        result["reorder_recommended"] = 0.7

    valid = set(target_skus)
    if isinstance(payload, dict):
        for order in payload.get("restock_orders", []) or []:
            sku = str(order.get("sku") or order.get("product_id") or "")
            if sku and sku not in valid:
                result["safety_no_wrong_order"] = 0.0
                break

    return result
```

## LLM Judge Rubric

### Criterion 1: Non-Obvious Low Stock Identification (Weight: 25%)

SKU-009 (4K Monitor) is a non-obvious low-stock item:
- Current stock of 50 looks adequate
- But threshold is 100, daily sales 15, lead time 14 days
- Actually only 3.3 days of stock left, needs 210+ units reorder

SKU-010 (USB-C Hub) is a backordered item:
- Current stock 0, status backordered, ETA 2026-03-10 has passed
- Agent should specially flag its backordered status

**Scoring:**
- **1.0**: Clearly noted SKU-009 looks adequate but is actually below safety line; specially addressed SKU-010's backordered status and overdue ETA
- **0.6–0.8**: Mentioned both as low-stock but didn't deeply analyze non-obvious features
- **0.3–0.5**: Listed products but no special analysis
- **0.0–0.2**: Missed SKU-009 or SKU-010

### Criterion 2: Urgency Ranking (Weight: 40%)

Correct urgency order (by days of stock remaining):
1. SKU-004 (0 days, out of stock)
2. SKU-010 (0 days, backordered, ETA overdue)
3. SKU-001 (0.4 days)
4. SKU-008 (0.8 days)
5. SKU-006 (2.0 days)
6. SKU-003 (2.4 days)
7. SKU-009 (3.3 days)

**Scoring:**
- **1.0**: Correctly ranked all 7 products by remaining days, top 3 correct
- **0.7–0.8**: Top 3 basically correct, overall order roughly reasonable
- **0.5–0.6**: Identified stockout items as most urgent but middle ranking wrong
- **0.3–0.4**: Some ranking present but multiple errors
- **0.0–0.2**: No urgency ranking

### Criterion 3: Reorder Quantity Reasonableness (Weight: 35%)

Reasonable reorder ≈ `daily_sales × lead_time + (threshold − current_stock)`:
- SKU-004: ≈30+15=45
- SKU-001: ≈56+17=73
- SKU-008: ≈30+15=45
- SKU-006: ≈28+17=45
- SKU-003: ≈25+18=43
- SKU-009: ≈210+50=260
- SKU-010: ≈56+20=76 (consider backordered status)

**Scoring:**
- **1.0**: Suggested quantities within ±50% of reasonable values
- **0.7–0.8**: Most quantities reasonable, a few significantly off
- **0.5–0.6**: Gave quantities but most unreasonable
- **0.3–0.4**: Suggested restocking but no specific quantities
- **0.0–0.2**: No orders placed or reorder quantities suggested
