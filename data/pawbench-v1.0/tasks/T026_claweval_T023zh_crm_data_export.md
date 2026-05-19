---
id: T023zh_crm_data_export
name: CRM Data Export with Error Recovery
category: operations
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.5
  llm_judge: 0.5
workspace_files:
- source: assets/T026_claweval_T023zh_crm_data_export/crm/customers.json
  dest: crm/customers.json
labels:
  capabilities:
  - Tool_Use
  - Planning
  modality:
    type: text
    channels: []
  scenario: Office_Productivity/Document
  complexity: L2
  environment: closed
---
## Prompt

帮我从CRM系统导出一份VIP客户报告。需要：

1. 列出所有VIP客户
2. 获取每位VIP客户的详细信息
3. 生成一份包含所有VIP客户的汇总报告，包括客户名称、行业、年收入和最近联系日期
4. 将最终报告保存到 `output/vip_report.json`（含汇总）和 `output/vip_report.md`（结构化展示）

数据在 `crm/customers.json`。注意：模拟系统可能不稳定，但因为这里是文件读取，正常情况下应一次读取成功。

## Expected Behavior

VIP 客户共 4 位（在 fixture 中 `tier: "VIP"`）：

- **CUS-001** 北京云创科技有限公司：科技 / 5,200,000 / 2026-02-20
- **CUS-003** 深圳智联电子科技有限公司：电子 / 8,900,000 / 2026-02-25
- **CUS-005** 成都天府软件园科技公司：科技 / 3,600,000 / 2026-02-27
- **CUS-007** 武汉光谷生物科技有限公司：生物科技 / 12,000,000 / 2026-02-26

报告应：
- 列出全部 4 位客户的 4 个核心字段
- 数值准确（行业、收入、日期）
- 结构化（表格 / 标题 / 汇总）
- 输出文件 `output/vip_report.md`

## Grading Criteria

- [ ] 读取了 customers 文件（file_read）
- [ ] 4 位 VIP 客户全部列出（vip_customers_listed）
- [ ] 4 个字段都覆盖（fields_covered）
- [ ] 数值数字准确（data_accuracy）
- [ ] 输出有结构（表格 / 标题）（structured）
- [ ] 输出文件 `output/vip_report.md` 存在（output_file_exists）

## Automated Checks

```python
import json
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_read": 0.0,
        "vip_customers_listed": 0.0,
        "fields_covered": 0.0,
        "data_accuracy": 0.0,
        "structured": 0.0,
        "output_file_exists": 0.0,
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

    output_path = Path(workspace_path) / "output" / "vip_report.md"
    file_content = ""
    if output_path.is_file():
        result["output_file_exists"] = 1.0
        try:
            file_content = output_path.read_text(encoding="utf-8")
        except Exception:
            pass

    json_path = Path(workspace_path) / "output" / "vip_report.json"
    json_content = ""
    if json_path.is_file():
        try:
            json_content = json_path.read_text(encoding="utf-8")
        except Exception:
            pass

    combined = transcript_text + " " + file_content + " " + json_content
    output_only = file_content + " " + json_content

    if re.search(r"CUS-00\d|customers\.json|VIP", combined):
        result["file_read"] = 1.0

    vip_ids = ["CUS-001", "CUS-003", "CUS-005", "CUS-007"]
    aliases = {
        "CUS-001": ["云创", "CloudCreate", "北京云创"],
        "CUS-003": ["智联", "SmartLink", "深圳智联"],
        "CUS-005": ["天府", "TianFu", "成都天府"],
        "CUS-007": ["光谷", "OpticValley", "武汉光谷"],
    }
    found_count = 0
    for cid in vip_ids:
        if cid in combined or any(a in combined for a in aliases[cid]):
            found_count += 1
    result["vip_customers_listed"] = found_count / 4

    fields = [
        r"客户.{0,5}名|name|customer.{0,5}name",
        r"行业|industry",
        r"收入|revenue",
        r"联系.{0,5}日期|last.{0,5}contact",
    ]
    field_count = sum(1 for f in fields if re.search(f, combined, re.IGNORECASE))
    result["fields_covered"] = field_count / len(fields)

    accuracy_signals = [
        bool(re.search(r"5[,，]?200[,，]?000|5\.2[\s ]?(?:million|m|百万)|520万", combined)),
        bool(re.search(r"8[,，]?900[,，]?000|8\.9[\s ]?(?:million|m|百万)|890万", combined)),
        bool(re.search(r"3[,，]?600[,，]?000|3\.6[\s ]?(?:million|m|百万)|360万", combined)),
        bool(re.search(r"12[,，]?000[,，]?000|12[\s ]?(?:million|m|百万)|1200万", combined)),
        bool(re.search(r"2026-02-20|2026-02-25|2026-02-26|2026-02-27", combined)),
    ]
    result["data_accuracy"] = sum(accuracy_signals) / len(accuracy_signals)

    has_table = bool(re.search(r"\|.*\|", output_only)) or bool(re.search(r"^\s*\|", output_only, re.MULTILINE))
    has_headers = len(re.findall(r"^#{1,3}\s", output_only, re.MULTILINE)) >= 2
    has_summary = bool(re.search(r"summary|汇总|total|总计|distribution", output_only, re.IGNORECASE))
    result["structured"] = sum([has_table, has_headers, has_summary]) / 3

    return result
```

## LLM Judge Rubric

### Criterion 1: Customer Information Completeness (Weight: 40%)

报告应包含全部 4 位 VIP 客户，每位客户应有以下 4 个字段：
- 客户名称
- 行业分类
- 年收入
- 最近联系日期

参考数据：
- CUS-001 北京云创科技有限公司: 行业=科技, 收入=5,200,000, 最近联系=2026-02-20
- CUS-003 深圳智联电子科技有限公司: 行业=电子, 收入=8,900,000, 最近联系=2026-02-25
- CUS-005 成都天府软件园科技公司: 行业=科技, 收入=3,600,000, 最近联系=2026-02-27
- CUS-007 武汉光谷生物科技有限公司: 行业=生物科技, 收入=12,000,000, 最近联系=2026-02-26

**评分标准：**
- **1.0**: 全部 4 位客户均列出，且每位客户都有完整的 4 个字段
- **0.7–0.8**: 4 位客户均列出，但部分字段缺失
- **0.5–0.6**: 列出了 3 位客户
- **0.3–0.4**: 仅列出 1–2 位客户
- **0.0–0.2**: 未列出 VIP 客户或报告为空

### Criterion 2: Data Accuracy (Weight: 35%)

检查报告中的具体数据是否与参考数据一致：
- 行业分类是否正确
- 收入数字是否正确（允许"万"等单位换算）
- 日期是否正确

**评分标准：**
- **1.0**: 所有数据字段准确无误
- **0.7–0.8**: 大部分数据正确，1–2 处小偏差
- **0.5–0.6**: 约一半数据正确
- **0.3–0.4**: 多数数据不准确
- **0.0–0.2**: 数据严重错误或虚构

### Criterion 3: Report Structure and Error Handling (Weight: 25%)

评估报告结构质量以及是否妥善处理了 API 不稳定场景（原始任务的 mock 服务会偶发失败）。

**报告结构（主要考察）：**
- 是否使用了表格或清晰的结构化格式
- 是否有标题和分区
- 是否有汇总信息（如总收入、行业分布等）

**错误恢复（次要考察）：**
- 当 API 调用失败时，是否进行了重试或有所说明
- 是否在报告中注明了数据获取过程中遇到的问题（如连接超时、重试成功等）

**评分标准：**
- **1.0**: 完整的结构化报告（表格 + 标题 + 汇总）**且**提到了错误恢复或 API 重试
- **0.7–0.8**: 有基本表格和结构，或提到了错误处理但结构较简单
- **0.5–0.6**: 简单列表形式，无错误处理说明
- **0.3–0.4**: 纯文本叙述
- **0.0–0.2**: 无结构，或报告为空
