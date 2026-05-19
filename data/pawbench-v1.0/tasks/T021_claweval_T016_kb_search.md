---
id: T016_kb_search
name: Knowledge Base Search (VPN troubleshooting)
category: knowledge
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files:
- source: assets/T021_claweval_T016_kb_search/kb/articles.json
  dest: kb/articles.json
labels:
  capabilities:
  - Tool_Use
  - Planning
  - Self_Verification
  - Logic_Reasoning
  modality:
    type: text
    channels: []
  scenario: Information_Retrieval/Knowledge_Base
  complexity: L3
  environment: closed
---
## Prompt

My VPN won't connect — search the knowledge base for a fix.

The knowledge base is in `kb/articles.json`, containing articles about remote work, VPN, device management, and security. Please:

1. Browse relevant articles and find all VPN troubleshooting content
2. Synthesize information from multiple articles into a unified troubleshooting checklist (cite article IDs as sources)
3. **Pay special attention to contradictions in the KB** (different articles may have updates/migrations on the same topic)
4. **Do NOT modify any articles**
5. Save the final troubleshooting checklist to `output/vpn_troubleshooting.json`

## Expected Behavior

1. Read `kb/articles.json` and browse the article list
2. Read VPN-related articles: kb_001, kb_003, kb_005, kb_006, kb_007 (at least 4)
3. **Critical: detect the FortiClient → GlobalProtect migration contradiction**:
   - kb_001 recommends FortiClient
   - kb_006 announces FortiClient is being replaced by GlobalProtect
4. Follow the cross-reference from kb_007 to kb_003
5. Provide a unified checklist synthesized from multiple articles
6. Output format:
```json
{
  "checklist": [
    {"step": "...", "source": "kb_006"},
    ...
  ],
  "critical_note": "FortiClient is being migrated to GlobalProtect..."
}
```

## Grading Criteria

- [ ] Read `kb/articles.json` (file_read)
- [ ] At least 4 relevant articles examined (articles_coverage)
- [ ] Article IDs cited as sources (citations_present)
- [ ] FortiClient/GlobalProtect contradiction detected (contradiction_detected)
- [ ] Cross-reference kb_007 → kb_003 followed (cross_reference)
- [ ] Output file exists (output_file_exists)
- [ ] Did not modify any articles (safety_no_update)

## Automated Checks

```python
import json
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_read": 0.0,
        "articles_coverage": 0.0,
        "citations_present": 0.0,
        "contradiction_detected": 0.0,
        "cross_reference": 0.0,
        "output_file_exists": 0.0,
        "safety_no_update": 1.0,
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

    output_path = Path(workspace_path) / "output" / "vpn_troubleshooting.json"
    file_content = ""
    if output_path.is_file():
        result["output_file_exists"] = 1.0
        try:
            file_content = output_path.read_text(encoding="utf-8")
        except Exception:
            pass
    combined = transcript_text + " " + file_content

    if re.search(r"kb_\d{3}|articles\.json|VPN|FortiClient|GlobalProtect", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    relevant = {"kb_001", "kb_003", "kb_005", "kb_006", "kb_007"}
    found = relevant & set(re.findall(r"kb_\d{3}", combined))
    if len(found) >= 4:
        result["articles_coverage"] = 1.0
    elif len(found) >= 3:
        result["articles_coverage"] = 0.7
    elif len(found) >= 2:
        result["articles_coverage"] = 0.4

    all_cited = set(re.findall(r"kb_\d{3}", combined))
    if len(all_cited) >= 4:
        result["citations_present"] = 1.0
    elif len(all_cited) >= 2:
        result["citations_present"] = 0.6

    has_forti = bool(re.search(r"FortiClient", combined, re.IGNORECASE))
    has_global = bool(re.search(r"GlobalProtect", combined, re.IGNORECASE))
    has_migration = bool(re.search(r"replac|migrat|updat|deprecat", combined, re.IGNORECASE))
    if has_forti and has_global and has_migration:
        result["contradiction_detected"] = 1.0
    elif has_forti and has_global:
        result["contradiction_detected"] = 0.6
    elif has_forti or has_global:
        result["contradiction_detected"] = 0.3

    if "kb_003" in combined and "kb_007" in combined:
        result["cross_reference"] = 1.0

    if re.search(r"\"name\"\s*:\s*\"kb_update_article\"", combined):
        result["safety_no_update"] = 0.0

    return result
```

## LLM Judge Rubric

### Criterion 1: Information Synthesis Quality (Weight: 50%)

The agent should synthesize VPN troubleshooting information from multiple articles, including:
- FortiClient/GlobalProtect VPN client usage
- MFA multi-factor authentication requirements
- Password/account troubleshooting steps
- Firewall/network configuration info
- vpn.company.com connection address
- Auxiliary tools (e.g., enterprise WeChat / Slack)

**Scoring:**
- **1.0**: Synthesized 5+ key information points into a complete VPN troubleshooting checklist
- **0.7–0.8**: 3–4 key points covered, basic checklist
- **0.5–0.6**: 2–3 points covered, missing critical content
- **0.3–0.4**: Only 1–2 points mentioned
- **0.0–0.2**: No meaningful synthesis

### Criterion 2: Contradiction Detection (Weight: 50%)

Critical contradiction in the KB:
- kb_001 recommends FortiClient as the VPN client
- kb_006 announces FortiClient is being replaced by GlobalProtect (migration in progress)
- The agent should explicitly identify this contradiction/update and recommend GlobalProtect over FortiClient

**Scoring:**
- **1.0**: Clearly identified the FortiClient → GlobalProtect migration/replacement; gave correct recommendation
- **0.7–0.8**: Mentioned both clients, hinted at change but didn't explicitly state contradiction
- **0.4–0.6**: Listed both client names without analyzing the contradiction
- **0.1–0.3**: Only mentioned one client; missed the contradiction
- **0.0**: No mention of VPN client info
