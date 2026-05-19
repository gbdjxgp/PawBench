---
id: T097_pinbench_eli5_model_summary
name: Pinbench ELI5 Model Summary
category: comprehension
grading_type: automated
timeout_seconds: 300
grading_weights:
  automated: 1.0
  llm_judge: 0.0
workspace_files:
- source: assets/T035_claweval_T097_pinbench_eli5_model_summary/docs/GPT4.txt
  dest: docs/GPT4.txt
labels:
  modality:
    type: text
    channels: []
  scenario: Content_Creation/Writing
  capabilities:
  - Tool_Use
  complexity: L2
  environment: closed
---
## Prompt

Read `docs/GPT4.txt` (an excerpt of the GPT-4 technical report), then **explain it like the reader is five years old**. Use simple words, short sentences, and everyday analogies. Aim for **about 200–400 words**.

Make sure you explain:
- What GPT-4 is
- What kinds of things it seems good at
- Why the researchers think it is important
- That it still has limits and can make mistakes

Save the ELI5 explanation to `output/eli5.md`.

## Expected Behavior

A child-friendly explanation that:
- Says what GPT-4 is (a big helper / smart computer program)
- Lists examples of what it can do (write, answer questions, code, etc.)
- Mentions why it matters (more advanced than older models, better at many tests)
- Notes that it is **not perfect** and can make mistakes
- Uses analogies ("like a", "imagine", "think of it as") and avoids heavy jargon
- ~200–400 words

## Grading Criteria

- [ ] Read the source document (file_read)
- [ ] Output file `output/eli5.md` exists (output_file_exists)
- [ ] Word count in 150–500 range, ideal 200–400 (word_count_score)
- [ ] Avoids technical jargon (simplicity)
- [ ] Uses everyday analogies (engagement)
- [ ] Covers all 4 required concepts (concepts_covered)
- [ ] Mentions limits / mistakes (accuracy_acknowledged)

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    """
    Mirrors original PinbenchEli5ModelSummaryGrader formula exactly:
      score = 0.25*simplicity + 0.25*concept_score + 0.15*engagement
            + 0.15*word_count_score + 0.10*tool_used + 0.10*accuracy_score
    """

    JARGON_WORDS = [
        "multimodal", "transformer", "rlhf", "benchmark", "parameters",
        "neural network", "fine-tuning", "token", "inference",
    ]
    ANALOGY_PHRASES = ["like a", "imagine", "pretend", "think of it as", "just like", "as if"]
    ACCURACY_KEYWORDS = ["gpt-4", "mistake", "not perfect", "wrong", "error", "careful"]
    WHAT_IS = ["gpt-4", "gpt4", "ai", "computer", "program", "model", "system", "brain"]
    GOOD_AT = ["good at", "can do", "help", "write", "answer", "solve", "understand",
               "read", "language", "math", "code", "task", "many things", "lots of things"]
    WHY_MATTERS = ["important", "matters", "big deal", "special", "powerful", "amazing",
                   "better", "smarter", "impressive", "breakthrough", "advance"]
    LIMITS = ["mistake", "wrong", "not perfect", "limit", "can't", "doesn't always",
              "not always", "careful", "error", "fail", "struggle", "imperfect"]

    def _all_text(msgs):
        parts = []
        for m in msgs:
            actual = m.get("message", m)
            if actual.get("role") not in ("assistant",):
                continue
            c = actual.get("content", "")
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, list):
                for b in c:
                    if isinstance(b, dict):
                        parts.append(b.get("text", ""))
        return " ".join(parts)

    transcript_text = _all_text(transcript)
    output_path = Path(workspace_path) / "output" / "eli5.md"
    file_content = ""
    if output_path.is_file():
        try:
            file_content = output_path.read_text(encoding="utf-8")
        except Exception:
            pass

    # Evaluate ELI5 quality on output file (preferred) or transcript
    review_text = file_content if file_content else transcript_text
    lower = review_text.lower()
    combined_lower = (transcript_text + " " + file_content).lower()

    # tool_used: agent read the GPT4.txt document
    tool_used = 1.0 if re.search(r"gpt.?4\.txt|documents_extract_text|read.*gpt", combined_lower) else 0.0

    # word_count_score
    word_count = len(review_text.split())
    if 200 <= word_count <= 400:
        word_count_score = 1.0
    elif 150 <= word_count < 200 or 400 < word_count <= 500:
        word_count_score = 0.7
    else:
        word_count_score = 0.4

    # simplicity: penalize jargon
    jargon_count = sum(1 for j in JARGON_WORDS if j in lower)
    if jargon_count == 0:
        simplicity = 1.0
    elif jargon_count == 1:
        simplicity = 0.7
    elif jargon_count == 2:
        simplicity = 0.4
    else:
        simplicity = 0.2

    # engagement: check for analogies
    analogy_count = sum(1 for a in ANALOGY_PHRASES if a in lower)
    engagement = 1.0 if analogy_count >= 2 else 0.5 if analogy_count == 1 else 0.2

    # concept_score: 4 required concept clusters
    concepts_covered = sum([
        any(kw in lower for kw in WHAT_IS),
        any(kw in lower for kw in GOOD_AT),
        any(kw in lower for kw in WHY_MATTERS),
        any(kw in lower for kw in LIMITS),
    ])
    concept_score = concepts_covered / 4

    # accuracy_keywords_score
    acc_count = sum(1 for kw in ACCURACY_KEYWORDS if kw in lower)
    accuracy_score = min(acc_count / 2, 1.0)

    # Final weighted score — matches original grader formula exactly
    weighted = round(
        0.25 * simplicity
        + 0.25 * concept_score
        + 0.15 * engagement
        + 0.15 * word_count_score
        + 0.10 * tool_used
        + 0.10 * accuracy_score,
        3,
    )
    return {"score": weighted}
```

## LLM Judge Rubric

> **注意：本任务 grading_type 为 automated，LLM judge 权重为 0。此处仅作参考文档，实际评分完全由 Automated Checks 的加权公式决定。**

原始 grader 为纯规则评分，无 LLM judge 调用：
- 0.25 × 避免技术术语（simplicity）
- 0.25 × 覆盖4个概念（concept_score）
- 0.15 × 使用类比（engagement）
- 0.15 × 字数 200-400（word_count_score）
- 0.10 × 读取了文档（tool_used）
- 0.10 × 提及局限性（accuracy_score）
