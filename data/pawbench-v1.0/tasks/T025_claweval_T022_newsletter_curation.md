---
id: T022_newsletter_curation
name: Newsletter Curation
category: content
grading_type: hybrid
timeout_seconds: 300
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files:
- source: assets/T025_claweval_T022_newsletter_curation/rss/articles.json
  dest: rss/articles.json
labels:
  capabilities:
  - Logic_Reasoning
  - Tool_Use
  - Planning
  modality:
    type: text
    channels: []
  scenario: Content_Creation/Writing
  complexity: L3
  environment: closed
---
## Prompt

Pick RSS articles relevant to our AI engineering team and publish a tech newsletter.

The RSS feed data is in `rss/articles.json` (13 articles total). Please:

1. Browse and read articles
2. Select articles relevant to AI/tech engineering (exclude entertainment, lifestyle, sports, real estate, etc.)
3. **Make explicit include/exclude decisions for borderline articles** (AI in film VFX, EU AI Act, blockchain+AI)
4. Write editorial summaries with insights — not just copy-paste titles
5. Compose a complete newsletter with title, foreword, sections, editor picks
6. Save the newsletter to `output/newsletter.md` (markdown format)

## Expected Behavior

**Definitely include (relevant)**:
- rss_001 (GPT-5 release)
- rss_003 (Kubernetes for AI workloads)
- rss_005 (Agent frameworks: LangGraph, CrewAI, etc.)
- rss_007 (RAG advances)
- rss_009 (open-source LLM benchmarks: Llama, Qwen, DeepSeek)

**Definitely exclude (irrelevant)**:
- rss_002 (entertainment), rss_004 (real estate), rss_006 (lifestyle), rss_008 (sports), rss_010 (health/anxiety)

**Borderline (require explicit reasoning)**:
- rss_011 (AI in Film VFX) — applied AI but not core engineering
- rss_012 (EU AI Act Compliance) — policy
- rss_013 (Blockchain + AI Decentralized Inference) — cross-domain

The newsletter should have:
- Title, foreword, organized sections (e.g., "LLM Updates", "Engineering Practice")
- Editor's picks / highlights
- Insightful summaries
- Decision rationale for borderline articles

## Grading Criteria

- [ ] Read articles file (file_read)
- [ ] At least 5 relevant articles included (relevant_articles)
- [ ] No irrelevant articles in newsletter (no_irrelevant)
- [ ] Borderline articles addressed with reasoning (borderline_addressed)
- [ ] Newsletter has clear structure (foreword/sections/picks) (structured)
- [ ] Output file `output/newsletter.md` exists (output_file_exists)

## Automated Checks

```python
import json
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_read": 0.0,
        "relevant_articles": 0.0,
        "no_irrelevant": 1.0,
        "borderline_addressed": 0.0,
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

    output_path = Path(workspace_path) / "output" / "newsletter.md"
    file_content = ""
    if output_path.is_file():
        result["output_file_exists"] = 1.0
        try:
            file_content = output_path.read_text(encoding="utf-8")
        except Exception:
            pass
    combined = transcript_text + " " + file_content
    newsletter_only = file_content if file_content else combined

    if re.search(r"rss_0\d{2}|articles\.json|GPT-?5|Kubernetes|Agent.{0,5}framework|RAG", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    relevant = ["rss_001", "rss_003", "rss_005", "rss_007", "rss_009"]
    relevant_topic = ["GPT-?5", "Kubernetes", "Agent.{0,5}framework|LangGraph|CrewAI", "RAG", "Llama|Qwen|DeepSeek"]
    by_id = sum(1 for r in relevant if r in newsletter_only)
    by_topic = sum(1 for t in relevant_topic if re.search(t, newsletter_only, re.IGNORECASE))
    score = max(by_id, by_topic) / 5
    result["relevant_articles"] = min(score, 1.0)

    irrelevant_terms = [r"divorce", r"housing.?price|real.?estate", r"kitchen|recipe",
                        r"soccer|football|sports", r"anxiety|mental.?health"]
    irrelevant_in_newsletter = sum(1 for t in irrelevant_terms if re.search(t, newsletter_only, re.IGNORECASE))
    if irrelevant_in_newsletter >= 2:
        result["no_irrelevant"] = 0.0
    elif irrelevant_in_newsletter == 1:
        result["no_irrelevant"] = 0.5

    borderline_topics = ["VFX|film", r"EU AI Act|AI Act|compliance", "blockchain|decentralized"]
    borderline_count = sum(1 for t in borderline_topics if re.search(t, combined, re.IGNORECASE))
    has_reasoning = bool(re.search(r"include|exclude|because|reason|borderline|edge.?case|judgment", combined, re.IGNORECASE))
    if borderline_count >= 2 and has_reasoning:
        result["borderline_addressed"] = 1.0
    elif borderline_count >= 1 and has_reasoning:
        result["borderline_addressed"] = 0.6
    elif borderline_count >= 1:
        result["borderline_addressed"] = 0.3

    has_title = bool(re.search(r"^#{1,3}\s|title\s*:|newsletter", newsletter_only, re.IGNORECASE | re.MULTILINE))
    has_sections = len(re.findall(r"^#{2,3}\s", newsletter_only, re.MULTILINE)) >= 2
    has_picks = bool(re.search(r"editor.{0,5}pick|highlight|featured|top pick", newsletter_only, re.IGNORECASE))
    structure_score = sum([has_title, has_sections, has_picks]) / 3
    result["structured"] = structure_score

    return result
```

## LLM Judge Rubric

### Criterion 1: Topic Coverage & Summary Quality (Weight: 35%)

The newsletter should cover these core AI/tech topics:
- GPT-5 release and new features
- Kubernetes for AI workloads
- Agent frameworks (LangGraph, CrewAI, etc.)
- RAG (Retrieval-Augmented Generation) advances
- Open-source LLM benchmarks (Llama, Qwen, DeepSeek)

Each article summary should:
- Accurately capture the article's core content
- Extract key technical insights
- Not merely copy the title or give vague descriptions

**Scoring:**
- **1.0**: Covers 4–5 core topics with accurate, insightful summaries
- **0.7–0.8**: Covers 3–4 topics with reasonable summaries
- **0.5–0.6**: Covers 2–3 topics, or summaries are too brief/generic
- **0.3–0.4**: Only 1–2 topics covered
- **0.0–0.2**: Almost no topic coverage or summaries

### Criterion 2: Editorial Quality (Weight: 35%)

The newsletter should demonstrate editorial value, not just list articles:
- Has a newsletter title and editorial foreword
- Articles organized into sections (e.g., "LLM Updates", "Engineering Practice")
- Editor's picks / highlights marked
- Connections drawn between articles (e.g., "GPT-5 vs open-source LLM competition")
- Clear structure with section headers

**Scoring:**
- **1.0**: Complete editorial framework (title+foreword+sections+picks+summary)
- **0.7–0.8**: Basic editorial structure with some recommendations
- **0.5–0.6**: Simple structure but lacks editorial perspective
- **0.3–0.4**: More like an article list than an edited newsletter
- **0.0–0.2**: Pure title listing

### Criterion 3: Borderline Article Handling (Weight: 30%)

Three borderline articles need special judgment:
- rss_011: AI in Film VFX (technically related but not core AI)
- rss_012: EU AI Act Compliance (policy related to AI)
- rss_013: Blockchain + AI Decentralized Inference (cross-domain)

The agent should make a clear include/exclude decision for each with reasoning:
- Consider the target audience (AI engineering team)
- Explain why each borderline article was included or excluded
- Demonstrate editorial judgment

**Scoring:**
- **1.0**: Clear decision with detailed reasoning for each borderline article
- **0.6–0.8**: Handled most borderline articles with adequate reasoning
- **0.3–0.5**: Mentioned borderline articles but no detailed reasoning
- **0.0–0.2**: Didn't discuss borderline articles, or simply included/excluded all
