---
id: T024_crm_data_export
name: CRM Data Export with Error Recovery
category: operations
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.5
  llm_judge: 0.5
workspace_files:
- source: assets/T027_claweval_T024_crm_data_export/crm/customers.json
  dest: crm/customers.json
labels:
  capabilities:
  - Tool_Use
  - Planning
  - Self_Verification
  modality:
    type: text
    channels: []
  scenario: Office_Productivity/Document
  complexity: L3
  environment: closed
---
## Prompt

Help me export a VIP customer report from the CRM system. Requirements:

1. List all VIP customers
2. Get detailed information for each VIP customer
3. Generate a summary report including customer name, industry, annual revenue, and last contact date
4. Save the final report to `output/vip_report.json` (with summary) and `output/vip_report.md` (structured presentation)

The data is in `crm/customers.json`.

## Expected Behavior

There are 4 VIP customers (`tier: "VIP"`):

- **CUS-001** CloudCreate Tech: Technology / 5,200,000 / 2026-02-20
- **CUS-003** SmartLink Electronics: Electronics / 8,900,000 / 2026-02-25
- **CUS-005** TianFu Software Park: Technology / 3,600,000 / 2026-02-27
- **CUS-007** OpticValley BioTech: Biotechnology / 12,000,000 / 2026-02-26

The report should:
- List all 4 customers with all 4 core fields
- Have accurate values (industry, revenue, dates)
- Be structured (table / headers / summary)
- Saved as `output/vip_report.md`

## Grading Criteria

- [ ] Read customers file (file_read)
- [ ] All 4 VIP customers listed (vip_customers_listed)
- [ ] All 4 fields covered (fields_covered)
- [ ] Numerical data accurate (data_accuracy)
- [ ] Output is structured (table / headers) (structured)
- [ ] Output file `output/vip_report.md` exists (output_file_exists)

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
        "CUS-001": ["CloudCreate"],
        "CUS-003": ["SmartLink"],
        "CUS-005": ["TianFu"],
        "CUS-007": ["OpticValley"],
    }
    found_count = 0
    for cid in vip_ids:
        if cid in combined or any(a in combined for a in aliases[cid]):
            found_count += 1
    result["vip_customers_listed"] = found_count / 4

    fields = [
        r"name|customer.{0,5}name",
        r"industry",
        r"revenue",
        r"last.{0,5}contact|contact.{0,5}date",
    ]
    field_count = sum(1 for f in fields if re.search(f, combined, re.IGNORECASE))
    result["fields_covered"] = field_count / len(fields)

    accuracy_signals = [
        bool(re.search(r"5[,]?200[,]?000|5\.2[\s]?(?:million|m\b)", combined)),
        bool(re.search(r"8[,]?900[,]?000|8\.9[\s]?(?:million|m\b)", combined)),
        bool(re.search(r"3[,]?600[,]?000|3\.6[\s]?(?:million|m\b)", combined)),
        bool(re.search(r"12[,]?000[,]?000|12[\s]?(?:million|m\b)", combined)),
        bool(re.search(r"2026-02-20|2026-02-25|2026-02-26|2026-02-27", combined)),
    ]
    result["data_accuracy"] = sum(accuracy_signals) / len(accuracy_signals)

    has_table = bool(re.search(r"\|.*\|", output_only))
    has_headers = len(re.findall(r"^#{1,3}\s", output_only, re.MULTILINE)) >= 2
    has_summary = bool(re.search(r"summary|total|distribution", output_only, re.IGNORECASE))
    result["structured"] = sum([has_table, has_headers, has_summary]) / 3

    return result
```

## LLM Judge Rubric

### Criterion 1: Customer Information Completeness (Weight: 40%)

The report should include all 4 VIP customers, each with 4 fields:
- Customer name
- Industry classification
- Annual revenue
- Last contact date

Reference data:
- CUS-001 CloudCreate Tech: industry=Technology, revenue=5,200,000, last_contact=2026-02-20
- CUS-003 SmartLink Electronics: industry=Electronics, revenue=8,900,000, last_contact=2026-02-25
- CUS-005 TianFu Software Park: industry=Technology, revenue=3,600,000, last_contact=2026-02-27
- CUS-007 OpticValley BioTech: industry=Biotechnology, revenue=12,000,000, last_contact=2026-02-26

**Scoring:**
- **1.0**: All 4 customers listed with all 4 fields each
- **0.7–0.8**: All 4 customers listed but some fields missing
- **0.5–0.6**: 3 customers listed
- **0.3–0.4**: Only 1–2 customers listed
- **0.0–0.2**: No VIP customers or empty report

### Criterion 2: Data Accuracy (Weight: 35%)

Check whether specific data values match the reference:
- Industry classifications correct
- Revenue figures correct (unit conversions like "million" acceptable)
- Dates correct

**Scoring:**
- **1.0**: All data fields accurate
- **0.7–0.8**: Most data correct, 1–2 minor deviations
- **0.5–0.6**: About half the data correct
- **0.3–0.4**: Most data inaccurate
- **0.0–0.2**: Data seriously wrong or fabricated

### Criterion 3: Report Structure and Error Handling (Weight: 25%)

Evaluate both the report structure quality and whether the agent appropriately handled the unstable API scenario (the original task's mock service has intermittent failures).

**Report Structure (primary):**
- Uses table or clear structured format
- Has title and sections
- Includes summary information (total revenue, industry distribution, etc.)

**Error Recovery (secondary):**
- When API calls fail, does the agent retry or explain what happened?
- Does the report mention any data retrieval issues encountered (e.g., timeouts, successful retries)?

**Scoring:**
- **1.0**: Complete structured report (table + title + summary) **and** mentions error recovery or API retries
- **0.7–0.8**: Basic table and structure, or mentions error handling but simpler structure
- **0.5–0.6**: Simple list format, no error handling mentioned
- **0.3–0.4**: Plain text narrative
- **0.0–0.2**: No structure, or report is empty
