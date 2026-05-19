---
id: T019zh_inventory_check
name: Inventory Check
category: operations
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.55
  llm_judge: 0.45
workspace_files:
- source: assets/T023_claweval_T019zh_inventory_check/inventory/products.json
  dest: inventory/products.json
labels:
  capabilities:
  - Logic_Reasoning
  - Math_Computation
  - Tool_Use
  - Planning
  modality:
    type: text
  scenario: Office_Productivity/Task_Management
  complexity: L3
  environment: open
---
## Prompt

看看库存哪些要补货了，帮我下单。

库存数据在 `inventory/products.json`。请：

1. 检查所有商品库存
2. 识别需要补货的商品（低于阈值的）
3. **特别注意"非显性"低库存**：库存数字看起来多但实际相对阈值/日销/补货周期不够（如某个 4K 显示器 50 台看似多但只够 3 天）
4. **特别注意 backordered 状态的商品**（库存 0 + ETA 已过）
5. 按紧急程度排序（剩余天数 = stock / daily_sales）
6. 给出合理补货量建议（公式：daily_sales × lead_time + (threshold − stock)）
7. 将分析结果保存到 `output/restock_plan.json`

## Expected Behavior

需要补货的商品共 7 个（按紧急程度排序）：

1. **SKU-004**（智能手表）：0 / 15，已断货 → 补 ~45 台
2. **SKU-010**（Type-C 扩展坞）：0 / 20，**backordered**，ETA 2026-03-10 已过 → 补 ~76 台，标注特殊状态
3. **SKU-001**（无线蓝牙耳机 Pro）：3 / 20，约 0.4 天 → 补 ~73 台
4. **SKU-008**（人体工学鼠标）：5 / 20，约 0.8 天 → 补 ~45 台
5. **SKU-006**（机械键盘）：8 / 25，约 2 天 → 补 ~45 台
6. **SKU-003**（笔记本电脑支架）：12 / 30，约 2.4 天 → 补 ~43 台
7. **SKU-009**（4K 显示器）：50 / 100，看似多但 daily_sales=15，lead_time=14 → 实际只够 3.3 天 → 补 ~260 台

输出格式：
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
- [ ] SKU-009 (4K monitor) flagged as non-obvious low stock (sku009_non_obvious)
- [ ] SKU-010 (Type-C 扩展坞) flagged as backordered with ETA past (sku010_backorder)
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

    # SKU-009 non-obvious: mentioned with reasoning about daily sales / threshold / not obvious
    if "SKU-009" in combined or "4K" in combined:
        if re.search(r"non.?obvious|3\.3|hidden|deceptive|看似|实际|不显眼|安全线", combined, re.IGNORECASE):
            result["sku009_non_obvious"] = 1.0
        else:
            result["sku009_non_obvious"] = 0.4

    # SKU-010 backordered
    if "SKU-010" in combined or "扩展坞" in combined:
        if re.search(r"backorder|ETA|2026-03-10|已过|过期|预订", combined, re.IGNORECASE):
            result["sku010_backorder"] = 1.0
        else:
            result["sku010_backorder"] = 0.4

    # Reorder recommended with quantity
    has_qty = bool(re.search(r"(?:quantity|qty|补货|reorder).*?(?:\d{2,4})", combined, re.IGNORECASE))
    if isinstance(payload, dict) and payload.get("restock_orders"):
        result["reorder_recommended"] = 1.0
    elif has_qty:
        result["reorder_recommended"] = 0.7

    # Safety: no SKU outside low-stock list ordered
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

SKU-009（4K 显示器）是一个"不显眼"的低库存商品：
- 当前库存 50 台看起来很多
- 但阈值 100 台、日销 15 台、补货周期 14 天
- 实际只够 3.3 天，需要补货 210+ 台

SKU-010（Type-C 扩展坞）是已缺货的预订商品：
- 当前库存 0，状态为 backordered，预计到货日 2026-03-10 已过
- agent 应特别标注该商品的特殊状态

**评分标准：**
- **1.0**: 明确指出 SKU-009 看似充足但实际低于安全线，且特别说明 SKU-010 的 backordered 状态和 ETA
- **0.6–0.8**: 提到了两者均为低库存，但未深入分析非显性特征
- **0.3–0.5**: 仅列出了产品名但未做特殊分析
- **0.0–0.2**: 遗漏了 SKU-009 或 SKU-010

### Criterion 2: Urgency Ranking (Weight: 40%)

正确的紧急排序（按剩余天数）：
1. SKU-004（0 天，已断货）
2. SKU-010（0 天，backordered，ETA 已过期）
3. SKU-001（0.4 天）
4. SKU-008（0.8 天）
5. SKU-006（2.0 天）
6. SKU-003（2.4 天）
7. SKU-009（3.3 天）

**评分标准：**
- **1.0**: 按剩余天数正确排序全部 7 个产品，前 3 最紧急的完全正确
- **0.7–0.8**: 前 3 最紧急的基本正确，整体排序大致合理
- **0.5–0.6**: 识别出断货产品最紧急，但中间排序有误
- **0.3–0.4**: 有一定排序但多处错误
- **0.0–0.2**: 没有紧急程度排序

### Criterion 3: Reorder Quantity Reasonableness (Weight: 35%)

合理补货量约等于 `daily_sales × lead_time + (threshold − current_stock)`：
- SKU-004: ≈ 30 + 15 = 45
- SKU-001: ≈ 56 + 17 = 73
- SKU-008: ≈ 30 + 15 = 45
- SKU-006: ≈ 28 + 17 = 45
- SKU-003: ≈ 25 + 18 = 43
- SKU-009: ≈ 210 + 50 = 260
- SKU-010: ≈ 56 + 20 = 76（需考虑 backordered 状态）

**评分标准：**
- **1.0**: 建议的补货量在合理范围的 ±50% 内
- **0.7–0.8**: 大部分数量合理，个别偏差较大
- **0.5–0.6**: 给出了数量但多数不够合理（如统一下 50 或过大）
- **0.3–0.4**: 建议了补货但没有给具体数量
- **0.0–0.2**: 没有下单或建议补货量
