---
id: CTB_D02_api_changelog
name: API Version Changelog
category: document_transform
grading_type: hybrid
timeout_seconds: 240
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T045_claweval_CTB_D02_api_changelog/fixtures/docs/api_v1_2.md
  dest: fixtures/docs/api_v1_2.md
- source: assets/T045_claweval_CTB_D02_api_changelog/fixtures/docs/api_v2_0.md
  dest: fixtures/docs/api_v2_0.md
labels:
  complexity: L2
  environment: closed
  capabilities:
  - Tool_Use
  - Logic_Reasoning
  scenario: Office_Productivity/Document
  modality:
    type: text
---
## Prompt

Compare the two attached API documentation versions in `fixtures/docs/` and produce a migration changelog for the engineering team.

Attachments:
- `fixtures/docs/api_v1_2.md`
- `fixtures/docs/api_v2_0.md`

Your output must:
1. Be written in English.
2. Explicitly cover the following topics:
   - Authentication endpoint
   - Event query endpoint
   - Order creation endpoint
   - New estimate endpoint
   - Webhook verification mechanism
   - Daily report endpoint migration
3. Use structured Markdown output containing at least:
   - A brief overview
   - A change table with columns: `Change Type`, `Section / Endpoint`, `Details`, `Impact Assessment`
   - A "Migration Priority / Recommendations" section
4. Use `ADD` / `REMOVE` / `MODIFY` for the change type.
5. The impact assessment must clearly indicate which changes are `Breaking` and which are `Non-breaking`.

Do not fabricate information that is not in the documents.

## Expected Behavior

1. Read both API documentation files from `fixtures/docs/`.
2. Identify and describe the 6 key changes:
   1. **Authentication**: `POST /v1/sessions` → `POST /v2/auth/tokens`; response fields changed from `session_id` / `expires_in_seconds` to `access_token` / `refresh_token` / `expires_in`. **Breaking**.
   2. **Event query**: `/v1/events` → `/v2/events`; query parameters changed from `start_date` / `end_date` / `page` to `from` / `to` / `cursor`; `page` removed; `event_count` renamed to `total`. **Breaking**.
   3. **Order creation**: `customer_id` → `account_id`; `amount_cents` → `amount` (decimal string); `currency` is now required. **Breaking**.
   4. **Estimate (new)**: `POST /v2/orders/estimate` added. **Non-breaking** (`ADD`).
   5. **Webhook verification**: `HMAC-SHA1` → `HMAC-SHA256`; new `X-Timestamp` header; 5-minute replay window. **Breaking**.
   6. **Daily report**: `GET /v1/reports/daily` → `GET /v2/reports/daily-summary`; old endpoint deprecated. **Breaking**.
3. Provide migration priority recommendations, with at least the orders schema, event query parameters, and webhook verification ranked as top priorities.

## Grading Criteria

- [ ] At least 4 of the 5 v2 endpoints are mentioned (`endpoint_coverage`).
- [ ] Change-type labels (ADD / REMOVE / MODIFY / Breaking / Non-breaking) appear (`change_labels_present`).
- [ ] Output uses a Markdown table (`table_structure_present`).
- [ ] LLM judge evaluates change accuracy, section completeness, and migration recommendations.

## Automated Checks

```python
def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "endpoint_coverage": 0.0,
        "change_labels_present": 0.0,
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
    lowered = text.lower()

    endpoints = ["/v2/auth/tokens", "/v2/events", "/v2/orders",
                 "/v2/orders/estimate", "/v2/reports/daily-summary"]
    found = sum(1 for ep in endpoints if ep in text)
    result["endpoint_coverage"] = min(found / 4, 1.0)

    # Accept any of these change-classification keywords. Agents often write
    # natural-English variants (deprecated / renamed / new endpoint) instead of
    # the strict "add/remove/modify" trio. Require 3 distinct hits for a 1.0,
    # which matches the original intent (a meaningful change taxonomy).
    labels = [
        "add", "added", "remove", "removed", "modify", "modified",
        "breaking", "non-breaking",
        "deprecated", "deprecate",
        "renamed", "rename",
        "new endpoint", "new field",
    ]
    label_hits = sum(1 for l in labels if l in lowered)
    result["change_labels_present"] = min(label_hits / 3, 1.0)

    if "|" in text and "---" in text:
        result["table_structure_present"] = 1.0

    return result
```

## LLM Judge Rubric

### Criterion 1: Change Accuracy (Weight: 36%)

Evaluate whether each API change is correctly identified with old → new details.

**Ground truth (6 changes):**
1. **Auth**: `POST /v1/sessions` → `POST /v2/auth/tokens`; `session_id` → `access_token` / `refresh_token`; **Breaking**.
2. **Events**: `/v1/events` → `/v2/events`; `page` → `cursor`, `start_date` / `end_date` → `from` / `to`, `event_count` → `total`; **Breaking**.
3. **Orders**: `customer_id` → `account_id`, `amount_cents` → `amount` (decimal), `currency` now required; **Breaking**.
4. **Estimate**: NEW `POST /v2/orders/estimate`; **Non-breaking** (ADD).
5. **Webhook**: `HMAC-SHA1` → `HMAC-SHA256`, new `X-Timestamp`, 5-min replay window; **Breaking**.
6. **Reports**: `/v1/reports/daily` → `/v2/reports/daily-summary`, old deprecated; **Breaking**.

**Scoring bands:**
- **0.9-1.0**: All 6 changes correctly described with old → new field mappings and breaking classification.
- **0.7-0.8**: 5-6 changes identified, most details correct.
- **0.5-0.6**: 3-4 changes identified with partial details.
- **0.3-0.4**: Only 1-2 changes.
- **0.0-0.2**: No meaningful change identification.

### Criterion 2: Section Completeness (Weight: 36%)

Evaluate whether all 6 API sections are covered.

**Required sections:**
1. Authentication (Auth): `/v1/sessions` → `/v2/auth/tokens`.
2. Event Query (Events): pagination and parameter changes.
3. Order Creation (Orders): field renames and type changes.
4. Estimate (Estimate): new endpoint.
5. Webhook Verification: signature algorithm upgrade.
6. Daily Report (Reports): endpoint rename and deprecation.

**Scoring bands:**
- **0.9-1.0**: All 6 sections explicitly covered.
- **0.7-0.8**: 5 sections covered.
- **0.5-0.6**: 3-4 sections covered.
- **0.3-0.4**: Only 1-2 sections.
- **0.0-0.2**: No structured coverage.

### Criterion 3: Migration Recommendations (Weight: 28%)

Evaluate the quality of migration priority recommendations.

**Expected elements:**
- Priority ranking: orders schema + webhook verification + event query params should be highest priority (Breaking changes).
- Estimate endpoint is low priority (non-breaking ADD).
- Timeline or phased migration suggestion.
- Risk assessment per change.

**Scoring bands:**
- **0.9-1.0**: Clear priority ranking with breaking vs non-breaking reasoning; specific migration steps.
- **0.7-0.8**: Has priorities and some reasoning.
- **0.5-0.6**: Generic migration advice.
- **0.3-0.4**: Minimal recommendation.
- **0.0-0.2**: No migration guidance.
