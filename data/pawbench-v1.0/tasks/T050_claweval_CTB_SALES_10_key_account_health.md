---
id: CTB_SALES_10_key_account_health
name: Key Account Health Assessment
category: data_analysis
grading_type: hybrid
timeout_seconds: 360
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files:
- source: assets/T050_claweval_CTB_SALES_10_key_account_health/fixtures/crm/customers.json
  dest: fixtures/crm/customers.json
- source: assets/T050_claweval_CTB_SALES_10_key_account_health/fixtures/finance/transactions.json
  dest: fixtures/finance/transactions.json
- source: assets/T050_claweval_CTB_SALES_10_key_account_health/fixtures/gmail/inbox.json
  dest: fixtures/gmail/inbox.json
labels:
  complexity: L3
  environment: closed
  capabilities:
  - Tool_Use
  - Planning
  - Math_Computation
  - Logic_Reasoning
  scenario: Data_Analytics/Business_Intelligence
  modality:
    type: text
    channels: []
---
## Prompt

You are the Key Account Director. Conduct a comprehensive **health assessment of all four strategic accounts** using the data already collected for you under `fixtures/`:

- `fixtures/crm/customers.json` — CRM record per key account: `name`, `company`, `deal_value` (annual contract), `notes` (renewal date, satisfaction tag, account manager).
- `fixtures/finance/transactions.json` — every revenue and credit/expense entry tied to the key accounts.
- `fixtures/gmail/inbox.json` — recent customer emails (sentiment signals, demands, complaints).

Follow these steps:
1. Read all three files.
2. For each key account, compute:
   - **Annual contract value** (from CRM `deal_value`).
   - **Cumulative revenue** = sum of `revenue` transactions − sum of `expense` (credit/compensation) transactions.
   - **Renewal date** and current **satisfaction** label (from CRM `notes`).
   - **Recent signal** from gmail (positive intent / complaint / churn risk / upsell opportunity).
3. Score each customer **1–10** across these dimensions:
   - **Financial contribution** (cumulative revenue, upsell trend).
   - **Satisfaction signals** (email sentiment, CRM satisfaction tag).
   - **Renewal risk** (days until renewal, competitor threats, complaints).
   - **Expansion potential** (upsell history, new demand signals).
4. Output a **key account health report** that includes:
   - For each account: name, annual contract value, cumulative revenue, an overall health score (1–10), the four dimension scores, key findings, and concrete action recommendations.
   - **Total annual contract value** across all 4 accounts.
   - **High-risk alerts** — which accounts need immediate action and why.
   - **Expansion opportunities** — which accounts to invest in for upsell/cross-sell.

Notes:
- All amounts are in CNY. Use a Markdown table where appropriate.
- The final response must be the report itself, not Python code or intermediate calculations.

## Expected Behavior

Per-account ground truth:

1. **XinYuan Group** — annual contract 2.5M; cumulative revenue 2.5M + 150K = **2.65M**; renewal 2026-06-30; satisfaction high; gmail signal: 30% efficiency uplift, **1M supply-chain expansion** intent, ready to renew. → Health **8–9 (healthy)**, expansion 1M.
2. **Zoomlion Heavy** — annual contract 1.8M; cumulative revenue 1.8M + 50K = **1.85M**; renewal 2026-05-15; satisfaction medium; gmail signal: **3 system outages**, threatening to switch vendor, possible 500K loss. → Health **4–5 (high risk)**, May renewal.
3. **BYD Electronics** — annual contract 3.2M; cumulative revenue 3.2M + 480K + 280K = **3.96M**; renewal 2026-09-01; satisfaction high; gmail signal: new Huizhou factory, **2M expansion** opportunity (biggest). → Health **8–9 (healthy)**, biggest expansion potential.
4. **Hisense Video** — annual contract 1.5M; cumulative revenue 1.5M − 80K compensation = **1.42M net** (gross 1.5M); renewal 2026-04-30 (most urgent); satisfaction low; gmail signal: **20% price-cut demand**, **SAP** competition threat, decision deadline end of April. → Health **3–4 (critical, most urgent)**.

Aggregate ground truth:
- **Total annual contract value: 9M** (2.5 + 1.8 + 3.2 + 1.5).
- **High-risk alerts**: Hisense (most urgent — April deadline + SAP threat) ranked above Zoomlion (May renewal + outages).
- **Expansion opportunities**: BYD (2M new factory) > XinYuan (1M supply chain).

## Grading Criteria

- [ ] All four accounts (XinYuan, BYD, Zoomlion, Hisense) explicitly named (`accounts_named`).
- [ ] Key cumulative-revenue figures present: 2.65M, 3.96M, total 9M (`financial_numbers_correct`).
- [ ] Hisense classified as **critical/highest risk**; Zoomlion as **high risk** (`risk_labels_correct`).
- [ ] Expansion opportunities: BYD 2M and XinYuan 1M both flagged (`expansion_flagged`).
- [ ] Each account has an explicit health score (1–10 scale visible) (`scores_present`).
- [ ] Output uses a Markdown table (`table_structure_present`).
- [ ] LLM judge evaluates per-account assessment accuracy and overall report quality.

## Automated Checks

```python
import re


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "accounts_named": 0.0,
        "financial_numbers_correct": 0.0,
        "risk_labels_correct": 0.0,
        "expansion_flagged": 0.0,
        "scores_present": 0.0,
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
    clean = (
        text.replace(",", "").replace("，", "")
        .replace("¥", "").replace("￥", "")
    )

    def get_region(s, kw, radius=500):
        idx = s.find(kw)
        return s[max(0, idx - 100): idx + radius] if idx >= 0 else ""

    # accounts_named — all 4 customers cited (English or Chinese).
    customers = [("XinYuan", "鑫源"), ("BYD", "比亚迪"),
                 ("Zoomlion", "中联"), ("Hisense", "海信")]
    found = sum(1 for en, zh in customers if en in text or zh in text)
    result["accounts_named"] = found / 4.0

    # financial_numbers_correct — 2.65M (XinYuan), 3.96M (BYD), 9M total.
    checks = [
        any(v in clean for v in ["2650000", "2.65M", "265万"]),
        any(v in clean for v in ["3960000", "3.96M", "396万"]),
        any(v in clean for v in ["9000000", "9M", "900万"]),
    ]
    result["financial_numbers_correct"] = sum(checks) / len(checks)

    # risk_labels_correct — Hisense critical, Zoomlion high-risk.
    his_region = get_region(text, "Hisense") or get_region(text, "海信")
    zl_region = get_region(text, "Zoomlion") or get_region(text, "中联")
    his_critical = bool(his_region) and any(
        kw in his_region.lower() for kw in
        ["critical", "most urgent", "highest risk", "severe", "高风险", "危险", "最紧急"]
    )
    zl_high = bool(zl_region) and any(
        kw in zl_region.lower() for kw in
        ["high risk", "high-risk", "warning", "danger", "outage", "风险", "预警", "宕机"]
    )
    result["risk_labels_correct"] = 0.5 * float(his_critical) + 0.5 * float(zl_high)

    # expansion_flagged — BYD 2M and XinYuan 1M expansion mentioned.
    byd_region = get_region(text, "BYD") or get_region(text, "比亚迪")
    xy_region = get_region(text, "XinYuan") or get_region(text, "鑫源")
    byd_expansion = bool(byd_region) and (
        ("2M" in byd_region or "2,000,000" in byd_region or "200万" in byd_region or "2000000" in byd_region.replace(",", ""))
        and any(k in byd_region.lower() for k in ["expansion", "expand", "factory", "upsell", "opportunit", "扩展", "新工厂"])
    )
    xy_expansion = bool(xy_region) and (
        ("1M" in xy_region or "1,000,000" in xy_region or "100万" in xy_region or "1000000" in xy_region.replace(",", ""))
        and any(k in xy_region.lower() for k in ["expansion", "expand", "supply chain", "upsell", "扩展", "供应链"])
    )
    result["expansion_flagged"] = 0.5 * float(byd_expansion) + 0.5 * float(xy_expansion)

    # scores_present — at least one numeric score on a 1–10 scale.
    if re.search(r"(?:\b|score[:\s]*)([3-9](?:\.\d)?)\s*(?:/|\s*out of\s*)\s*10", lower):
        result["scores_present"] = 1.0
    elif re.search(r"score[:\s]*[3-9]", lower) or re.search(r"评分[:：\s]*[3-9]", text):
        result["scores_present"] = 0.6

    # table_structure_present
    if "|" in text and "---" in text:
        result["table_structure_present"] = 1.0

    return result
```

## LLM Judge Rubric

### Criterion 1: Per-Account Assessment Accuracy (Weight: 54%)

Evaluate the accuracy of the health assessment for each key account.

**Ground truth — 4 key accounts:**

1. **XinYuan Group** — cumulative revenue 2.65M; satisfaction high; renewal low risk; expansion potential 1M (supply chain module). Health 8–9 (healthy).
2. **BYD Electronics** — cumulative revenue 3.96M; satisfaction high; new Huizhou factory → 2M expansion opportunity (biggest). Health 8–9 (healthy, best expansion).
3. **Zoomlion Heavy** — cumulative revenue 1.85M; 3 system outages, complaints; renewal in May, threatening to switch vendors; possible 500K loss. Health 4–5 (high risk).
4. **Hisense Video** — gross revenue 1.5M, net 1.42M after 80K compensation; low satisfaction, demanding 20% price cut; April deadline (most urgent), SAP competition threat. Health 3–4 (critical, most urgent).

**Scoring bands:**
- **0.9–1.0**: All 4 accounts with correct health classification; key numbers match; risk ordering correct (Hisense > Zoomlion).
- **0.7–0.8**: All 4 accounts assessed; most data correct; reasonable health scores.
- **0.5–0.6**: 3+ accounts assessed; some correct data.
- **0.3–0.4**: 1–2 accounts with meaningful assessment.
- **0.0–0.2**: No meaningful assessment.

### Criterion 2: Report Quality & Completeness (Weight: 46%)

Evaluate the structure and completeness of the report.

**Expected report structure:**
1. Per-account section: name, annual contract, cumulative revenue, health score, dimension scores, key findings, action items.
2. Total annual contract value: **9M** (2.5 + 1.8 + 3.2 + 1.5).
3. High-risk alert: Hisense (most urgent, April deadline) and Zoomlion (May renewal).
4. Expansion opportunities: BYD (2M new factory) and XinYuan (1M supply chain).
5. Priority action recommendations.

**Scoring bands:**
- **0.9–1.0**: Complete structured report with all 5 elements; correct total; clear risk prioritization.
- **0.7–0.8**: Per-account + summary sections; total mostly correct; some prioritization.
- **0.5–0.6**: Per-account data present but missing summary or incorrect total.
- **0.3–0.4**: Partial accounts; no overall summary.
- **0.0–0.2**: No coherent report.
