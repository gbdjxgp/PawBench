---
id: CTB_D03_whitepaper_architecture_report
name: Whitepaper Architecture Comparison Report
category: document_transform
grading_type: hybrid
timeout_seconds: 240
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T046_claweval_CTB_D03_whitepaper_architecture_report/fixtures/docs/system_x_whitepaper.md
  dest: fixtures/docs/system_x_whitepaper.md
- source: assets/T046_claweval_CTB_D03_whitepaper_architecture_report/fixtures/docs/system_y_whitepaper.md
  dest: fixtures/docs/system_y_whitepaper.md
- source: assets/T046_claweval_CTB_D03_whitepaper_architecture_report/fixtures/docs/system_z_whitepaper.md
  dest: fixtures/docs/system_z_whitepaper.md
labels:
  complexity: L3
  environment: open
  capabilities:
  - Tool_Use
  - Planning
  - Logic_Reasoning
  scenario: Office_Productivity/Document
  modality:
    type: text
---
## Prompt

Analyze the 3 attached technical whitepapers in `fixtures/docs/` and produce a technology-selection comparison report for the technical committee.

Attachments:
- `fixtures/docs/system_x_whitepaper.md`
- `fixtures/docs/system_y_whitepaper.md`
- `fixtures/docs/system_z_whitepaper.md`

Your output must:
1. Be written in English.
2. Cover the following four categories of information for each system:
   - Performance benchmark data
   - Architectural limitations
   - Hardware requirements
   - Suitable use cases
3. Use structured Markdown output containing at least:
   - A brief executive summary
   - A comparison table with columns: `Dimension`, `System X`, `System Y`, `System Z`
   - A conclusion section that clearly states which system is best suited for a "high-concurrency read-write real-time analytics" scenario
4. Do not fabricate information that is not in the attachments.
5. The conclusion must not simply say "it depends" — provide a definitive recommendation with rationale.

Hints:
- Pay special attention to throughput, P99 latency, node scale limits, and memory/disk constraints.
- If a system is clearly unsuitable for a particular scenario, state that explicitly.

## Expected Behavior

1. Read all three whitepapers from `fixtures/docs/`.
2. Cover the three systems with these key facts:
   - **System X** (distributed object storage): 420k ops/s, p99 18ms, 12-node soft limit, 64GB RAM + NVMe, weakness: cross-region write not recommended; metadata compaction window.
   - **System Y** (memory-first analytics engine): 710k ops/s, p99 4ms, 8-node coherence limit, 256GB RAM, weakness: coherence overhead grows steeply beyond 8 nodes; high memory cost.
   - **System Z** (graph-optimized database): 160k ops/s, traversal latency 7ms, 6-shard limit before write path degrades, 128GB RAM, weakness: NOT suitable for write-intensive real-time analytics; re-balancing overhead.
3. Recommend **System Y** as the top choice for "high-concurrency read-write real-time analytics" because it has the highest throughput and lowest p99 latency. Explicitly state that **System Z is not suitable** for this scenario.
4. Mention System Y trade-offs: high memory cost and 8-node coherence limit.

## Grading Criteria

- [ ] All three systems (X / Y / Z) are mentioned (`systems_mentioned`).
- [ ] Key throughput numbers (420k / 710k / 160k ops/s) are present (`throughput_numbers_present`).
- [ ] Output uses a Markdown comparison table (`table_structure_present`).
- [ ] A "Recommendation" or "Conclusion" section is present (`recommendation_section_present`).
- [ ] LLM judge evaluates technical-data accuracy and analysis / recommendation quality.

## Automated Checks

```python
import re


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "systems_mentioned": 0.0,
        "throughput_numbers_present": 0.0,
        "table_structure_present": 0.0,
        "recommendation_section_present": 0.0,
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
    normalized = text.replace(",", "")
    lowered = normalized.lower()

    def _has_system(letter):
        targets = [f"system {letter}", f"system{letter}",
                   f"system-{letter}", f"system_{letter}"]
        return any(t in lowered for t in targets)

    def _has_bounded(num):
        return bool(re.search(rf'(?<!\d){re.escape(num)}(?!\d)', normalized))

    names_found = sum(1 for letter in ["x", "y", "z"] if _has_system(letter))
    result["systems_mentioned"] = min(names_found / 3, 1.0)

    nums_found = 0
    for n in ["420", "710", "160"]:
        if _has_bounded(n) and ("k" in lowered or "ops" in lowered):
            nums_found += 1
    result["throughput_numbers_present"] = min(nums_found / 3, 1.0)

    if "|" in text and "---" in text:
        result["table_structure_present"] = 1.0

    if "recommend" in lowered or "conclusion" in lowered:
        result["recommendation_section_present"] = 1.0

    return result
```

## LLM Judge Rubric

### Criterion 1: Technical Data Accuracy (Weight: 50%)

Evaluate the accuracy and completeness of technical data for all three systems.

**Ground truth:**

#### System X (distributed object storage)
- Throughput: 420k ops/s.
- P99 latency: 18ms.
- Cluster limit: 12 nodes (soft limit).
- Hardware: 64GB RAM + NVMe.
- Weakness: cross-region write replication not recommended; metadata compaction window.

#### System Y (memory-first analytics engine)
- Throughput: 710k ops/s.
- P99 latency: 4ms.
- Cluster limit: 8 nodes (coherence cost spikes beyond 8).
- Hardware: 256GB RAM.
- Weakness: coherence overhead grows steeply beyond 8 nodes; high memory cost.

#### System Z (graph-optimized database)
- Throughput: 160k ops/s.
- Traversal latency: 7ms.
- Sharding: 6 shards max before write path degrades.
- Hardware: 128GB RAM.
- Weakness: NOT suitable for write-intensive real-time analytics; re-balancing overhead.

**Scoring bands:**
- **0.9-1.0**: All 3 systems covered with correct throughput, latency, cluster limits, hardware, and weaknesses.
- **0.7-0.8**: All 3 systems covered, most data correct, 1-2 minor omissions.
- **0.5-0.6**: 2-3 systems covered but significant data gaps or errors.
- **0.3-0.4**: Only 1-2 systems with meaningful data.
- **0.0-0.2**: No meaningful technical data.

**Penalty:** Inventing specs not in the whitepapers — deduct 0.2.

### Criterion 2: Analysis & Recommendation Quality (Weight: 50%)

Evaluate the quality of the comparison analysis and the final recommendation.

**Context:**
- Target scenario: "high-concurrency read-write for real-time analytics".
- Correct recommendation: **System Y** (highest throughput 710k, lowest p99 4ms, suitable for real-time analytics).
- Caveats: high memory cost, 8-node coherence limit.
- **System Z** should be explicitly noted as NOT suitable for this scenario.

**Expected elements:**
1. Structured comparison table (dimensions × systems).
2. Clear recommendation of System Y for the target scenario with rationale.
3. Explanation of why System Z is not suitable (write-intensive degradation).
4. Mention of System Y's trade-offs (memory cost, node limit).

**Scoring bands:**
- **0.9-1.0**: Has comparison table + clear Y recommendation + Z exclusion + trade-off discussion.
- **0.7-0.8**: Has comparison and recommendation, may lack depth on trade-offs.
- **0.5-0.6**: Some comparison but unstructured; recommendation exists but rationale is thin.
- **0.3-0.4**: Minimal comparison; no clear recommendation.
- **0.0-0.2**: No meaningful analysis.
