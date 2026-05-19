---
id: CTB_OPS_04_cross_team_dependency_map
name: Cross-Team Dependency Map
category: data_analysis
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.35
  llm_judge: 0.65
workspace_files:
- source: assets/T049_claweval_CTB_OPS_04_cross_team_dependency_map/fixtures/gmail/inbox.json
  dest: fixtures/gmail/inbox.json
- source: assets/T049_claweval_CTB_OPS_04_cross_team_dependency_map/fixtures/todo/tasks.json
  dest: fixtures/todo/tasks.json
labels:
  complexity: L3
  environment: closed
  capabilities:
  - Logic_Reasoning
  - Tool_Use
  - Planning
  scenario: Data_Analytics/Business_Intelligence
  modality:
    type: text
    channels: []
---
## Prompt

Analyze cross-team task dependencies and identify blocking chains and risks. The data has been pre-fetched for you in two attachments under `fixtures/`:

- `fixtures/gmail/inbox.json` — recent inter-team emails describing dependencies, blockers and delays.
- `fixtures/todo/tasks.json` — current pending tasks, each with `assignee` (e.g. `dba@…`, `backend@…`), `due_date`, and a `description` that often references upstream tasks.

Requirements:
1. Read both files, then **reconstruct the dependency graph** between teams (`pm`, `design`, `frontend`, `backend`, `dba`, `ops`, `security`, `qa`, `payment`).
2. Map out the dependency chains — describe them in text using arrows (`→`).
3. Identify **critical blocking chains**: which tasks are being blocked, and by whom.
4. Identify **delay risks**: which tasks may not be completed on time because of upstream slippage.
5. Find the **bottleneck team(s)** — the team(s) sitting on the critical path of the most chains.
6. Produce concrete, prioritized **recommendations** to unblock the dependencies.

Output a complete cross-team dependency analysis report (Markdown).

Notes:
- The final response must be the report itself, not Python code or intermediate calculations.

## Expected Behavior

Three independent dependency chains are visible across the gmail + todo data:

1. **Chain 1 — User Service**: `ops (database cluster deploy)` → `dba (user table migration)` → `backend (/api/v1/users refactor)` → `frontend (page adaptation)`.
2. **Chain 2 — Design Flow**: `pm (requirements confirmation)` → `design (mockups)` → `frontend (page adaptation)`.
3. **Chain 3 — Payment Launch**: `security (penetration test)` + `ops (production environment)` + `qa (regression testing)` → `payment launch`.

Critical path: `ops → dba → backend → frontend`.
Bottleneck team: **ops** — appears on both Chain 1 and Chain 3.

Delay risk: the `dba` user-table migration slipped from **3/26 → 3/29**, which cascades into `backend (3/28)` and `frontend (3/30)` — the user-service track is at high risk of missing its frontend deadline. The payment launch (target 4/1) is also at risk because `qa` still has 5 failing cases and `ops` has not finished the prod-env config.

Recommendations should:
- Prioritize unblocking **ops** first (resolves chains 1 and 3 simultaneously).
- Accelerate the dba migration once ops finishes its cluster work.
- Push pm to finalize requirements ASAP so design → frontend can progress in parallel.

## Grading Criteria

- [ ] Both data sources referenced (gmail + todo) (`sources_referenced`).
- [ ] At least 5 distinct team nodes named (e.g. ops, dba, backend, frontend, design, security, payment) (`chain_nodes_present`).
- [ ] Dependency notation present — `depend`, `block`, or `→` arrows (`dependency_concepts_present`).
- [ ] Bottleneck identified as `ops` AND the term `bottleneck` / `critical path` appears (`bottleneck_correct`).
- [ ] Delay-cascade analysis present: mentions `delay`/`postpone` AND `cascade`/`downstream`/`propagate` AND the date `3/29` / `March 29` / `29` (`delay_risk_analyzed`).
- [ ] Output uses a Markdown table or arrow notation (`structure_present`).
- [ ] LLM judge evaluates chain accuracy and risk-analysis quality.

## Automated Checks

```python
import re


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "sources_referenced": 0.0,
        "chain_nodes_present": 0.0,
        "dependency_concepts_present": 0.0,
        "bottleneck_correct": 0.0,
        "delay_risk_analyzed": 0.0,
        "structure_present": 0.0,
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

    # sources_referenced
    gmail_seen = bool(re.search(r"inbox\.json|gmail|email", lower))
    todo_seen = bool(re.search(r"tasks\.json|todo|task list|task[s]? data", lower))
    result["sources_referenced"] = 0.5 * float(gmail_seen) + 0.5 * float(todo_seen)

    # chain_nodes_present — at least 5 of 7 team labels.
    nodes = ["ops", "dba", "backend", "frontend", "design", "security", "payment"]
    found = sum(1 for n in nodes if n in lower)
    result["chain_nodes_present"] = min(found / 5, 1.0)

    # dependency_concepts_present — depend / block / arrow.
    dep_kw = ["depend", "block", "wait", "blocked", "blocking"]
    kw_hits = sum(1 for kw in dep_kw if kw in lower)
    has_arrow = ("→" in text) or ("->" in text)
    if kw_hits >= 2 or (kw_hits >= 1 and has_arrow):
        result["dependency_concepts_present"] = 1.0
    elif kw_hits >= 1 or has_arrow:
        result["dependency_concepts_present"] = 0.5

    # bottleneck_correct — explicitly names ops as the bottleneck/critical path.
    if "ops" in lower and any(kw in lower for kw in ["bottleneck", "critical path", "most critical"]):
        result["bottleneck_correct"] = 1.0
    elif any(kw in lower for kw in ["bottleneck", "critical path"]):
        result["bottleneck_correct"] = 0.4

    # delay_risk_analyzed — delay + cascade + the slippage date.
    delay = any(kw in lower for kw in ["delay", "postpone", "deferred", "slip", "推迟", "延期"])
    cascade = any(kw in lower for kw in ["cascade", "downstream", "propagat", "chain reaction", "knock-on", "ripple"])
    date_seen = bool(re.search(r"3[/-]29|march\s*29|29.*march", lower)) or "3/29" in text
    score = 0.34 * float(delay) + 0.33 * float(cascade) + 0.33 * float(date_seen)
    result["delay_risk_analyzed"] = round(min(score, 1.0), 2)

    # structure_present — markdown table or arrow chain.
    if ("|" in text and "---" in text) or ("→" in text) or ("->" in text):
        result["structure_present"] = 1.0

    return result
```

## LLM Judge Rubric

### Criterion 1: Dependency Chain Accuracy (Weight: 54%)

Evaluate the accuracy of dependency-chain identification.

**Ground truth — 3 dependency chains:**
- **Chain 1 (User Service)**: ops (cluster deploy) → dba (user table migration) → backend (API refactor) → frontend (page adaptation).
- **Chain 2 (Design Flow)**: pm (requirements confirmation) → design (mockups) → frontend (page adaptation).
- **Chain 3 (Payment Launch)**: security (pen-test) + ops (prod env) + qa (regression) → payment launch.

Critical path: `ops → dba → backend → frontend`.
Bottleneck: **ops** (appears in both chains 1 and 3).

**Scoring bands:**
- **0.9–1.0**: All 3 chains correctly mapped; critical path identified; bottleneck (ops) named.
- **0.7–0.8**: 2–3 chains correct; bottleneck identified.
- **0.5–0.6**: 1–2 chains partially correct; some blocking noted.
- **0.3–0.4**: Minimal chain identification.
- **0.0–0.2**: No dependency mapping.

### Criterion 2: Delay-Risk Analysis & Recommendations (Weight: 46%)

Evaluate the quality of delay-risk analysis and recommendations.

**Ground truth:**
- DBA migration slipped from 3/26 to 3/29 → cascade delay to backend (3/28) and frontend (3/30).
- Ops team is the bottleneck (appears in chains 1 and 3).
- Recommendations should prioritize unblocking ops first, then accelerating the dba migration.
- Parallelize where possible (e.g. pm → design path runs alongside ops → dba path).

**Scoring bands:**
- **0.9–1.0**: Delay quantified with the 3/29 date; cascade impact traced to backend/frontend; ops bottleneck addressed; specific unblocking actions listed.
- **0.7–0.8**: Delay mentioned; cascade noted; some recommendations.
- **0.5–0.6**: Some delay awareness; general recommendations.
- **0.3–0.4**: Minimal risk analysis.
- **0.0–0.2**: No risk analysis.
