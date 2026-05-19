---
id: M074_doc_extraction_thinking_impact
name: Document Extraction - Thinking Mode Impact
category: multimodal
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.66
  llm_judge: 0.34
workspace_files:
- source: assets/T009_claweval_M074_doc_extraction_thinking_impact/fixtures/GroundingME.pdf
  dest: fixtures/GroundingME.pdf
labels:
  capabilities:
  - Tool_Use
  - Math_Computation
  - Code_Manipulation
  - Planning
  modality:
    type: multimodal
    channels:
    - image
  scenario: Data_Analytics/Business_Intelligence
  complexity: L3
  environment: closed
---
## Prompt

The workspace contains:
- `fixtures/GroundingME.pdf` — the GroundingME paper

Analyze how much the **"Thinking" mode** improves model performance — focus exclusively on the **open-source** models evaluated in **Figure 5** of this paper.

Steps:
1. From **Table 3**, extract each open-source model's baseline `Total` accuracy (No-Think)
2. From **Figure 5**, extract each model's `Think` accuracy
3. Compute the relative percentage increase: `(Think − Base) / Base × 100`, rounded to 2 decimal places
4. **Exclude Seed-1.6-V** (commercial model per Section 4.1)
5. Save a CSV at `output/thinking_relative_impact.csv` with columns:
   `model, baseline, thinking, relative_increase`
   sorted in **descending** order of `relative_increase`
6. Generate a **vertical bar chart** at `output/relative_gain_bar.png` visualizing the sorted relative percentage increases

**Ground-truth values (6 open-source models, sorted descending):**

| Model | Baseline | Think | Relative Increase |
|---|---|---|---|
| MiMo-VL-7B-RL | 18.6 | 24.1 | 29.57% |
| Qwen3-VL-32B | 39.5 | 46.9 | 18.73% |
| Qwen3-VL-8B | 31.0 | 34.3 | 10.65% |
| Qwen3-VL-A22B | 45.1 | 49.8 | 10.42% |
| Qwen3-VL-A3B | 35.7 | 39.2 | 9.80% |
| GLM-4.5V | 32.1 | 34.0 | 5.92% |

## Expected Behavior

- Read the PDF
- Extract baseline + think numbers
- Filter out Seed-1.6-V; keep exactly 6 open-source models
- Save CSV (sorted descending by relative_increase)
- Save vertical bar chart PNG

## Grading Criteria

- [ ] Reads PDF (file_read)
- [ ] CSV exists (csv_exists)
- [ ] PNG exists (png_exists)
- [ ] Seed-1.6-V excluded (seed_excluded)
- [ ] All 6 open-source models present (models_complete)
- [ ] Relative-increase values correct (relative_correct)
- [ ] Sorted descending by relative_increase (sorted_desc)
- [ ] PNG substantial (png_substantial)

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_read": 0.0,
        "csv_exists": 0.0,
        "png_exists": 0.0,
        "seed_excluded": 1.0,
        "models_complete": 0.0,
        "relative_correct": 0.0,
        "sorted_desc": 0.0,
        "png_substantial": 0.0,
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

    csv_path = Path(workspace_path) / "output" / "thinking_relative_impact.csv"
    png_path = Path(workspace_path) / "output" / "relative_gain_bar.png"

    csv_content = ""
    if csv_path.is_file():
        result["csv_exists"] = 1.0
        try:
            csv_content = csv_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    if png_path.is_file():
        result["png_exists"] = 1.0
        try:
            size = png_path.stat().st_size
            if size > 5000:
                result["png_substantial"] = 1.0
            elif size > 2000:
                result["png_substantial"] = 0.5
        except Exception:
            pass

    combined = transcript_text + " " + csv_content

    if re.search(r"GroundingME|Table\s*3|Figure\s*5|baseline|thinking", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    if re.search(r"Seed-?1\.6", csv_content, re.IGNORECASE):
        result["seed_excluded"] = 0.0

    targets = ["MiMo-VL-7B-RL", "Qwen3-VL-32B", "Qwen3-VL-8B", "Qwen3-VL-A22B", "Qwen3-VL-A3B", "GLM-4.5V"]
    found = sum(1 for t in targets if re.search(re.escape(t).replace("-", "[-_ ]?"), csv_content, re.IGNORECASE))
    if found >= 6:
        result["models_complete"] = 1.0
    elif found >= 4:
        result["models_complete"] = 0.6
    elif found >= 2:
        result["models_complete"] = 0.3

    rel_targets = ["29.57", "18.73", "10.65", "10.42", "9.80", "5.92"]
    rel_hits = sum(1 for v in rel_targets if v in csv_content)
    if rel_hits >= 5:
        result["relative_correct"] = 1.0
    elif rel_hits >= 3:
        result["relative_correct"] = 0.6
    elif rel_hits >= 1:
        result["relative_correct"] = 0.3

    if csv_content:
        nums = re.findall(r"\d+\.\d+", csv_content)
        rel_nums = []
        seen_target = False
        for n in nums:
            try:
                f = float(n)
                if 4 < f < 35:
                    rel_nums.append(f)
            except Exception:
                continue
        candidate = []
        for v in rel_nums:
            if v in [29.57, 18.73, 10.65, 10.42, 9.80, 9.8, 5.92]:
                candidate.append(v)
        if len(candidate) >= 4:
            sorted_check = candidate == sorted(candidate, reverse=True)
            if sorted_check:
                result["sorted_desc"] = 1.0
            else:
                result["sorted_desc"] = 0.3
        elif candidate:
            result["sorted_desc"] = 0.5

    return result
```

## LLM Judge Rubric

### Criterion 1: Data Accuracy & Filtering (Weight: 66%)

**Ground truth (6 open-source models, sorted by relative increase descending):**

| Model | Baseline | Think | Relative Increase |
|---|---|---|---|
| MiMo-VL-7B-RL | 18.6 | 24.1 | 29.57% |
| Qwen3-VL-32B | 39.5 | 46.9 | 18.73% |
| Qwen3-VL-8B | 31.0 | 34.3 | 10.65% |
| Qwen3-VL-A22B | 45.1 | 49.8 | 10.42% |
| Qwen3-VL-A3B | 35.7 | 39.2 | 9.80% |
| GLM-4.5V | 32.1 | 34.0 | 5.92% |

**Note**: Seed-1.6-V must be **excluded** (commercial per Section 4.1).

**Award:**
- **+0.5 — Information filtering & math accuracy**: agent filtered out Seed-1.6-V; exactly 6 open-source models remain; baseline & thinking values match Table 3 / Figure 5; relative percentage correctly computed `(Think − Base) / Base × 100` rounded to 2dp.
  - 0 if Seed-1.6-V is included, any model missing, or relative percentages wrong.
- **+0.5 — Relational logic & sorting**: rows strictly sorted descending by `relative_increase` (MiMo-VL-7B-RL first, GLM-4.5V last).
  - 0 if sort order wrong.

**Scoring bands:**
- **1.0**: Both awarded
- **0.5**: One awarded
- **0.0**: Neither

### Criterion 2: Chart Quality (Weight: 34%)

Inspect `output/relative_gain_bar.png`:

- Vertical bar chart
- Exactly 6 open-source models
- Bars sorted descending (MiMo-VL-7B-RL highest, GLM-4.5V lowest)
- Heights approximately match: 29.57, 18.73, 10.65, 10.42, 9.80, 5.92
- Model names on x-axis fully readable (no overlap / cropping)
- Axis labels present

**Scoring bands:**
- **1.0**: All criteria met
- **0.5–0.8**: Minor issues (label overlap, slight ordering issue)
- **0.0–0.4**: Wrong chart type, wrong number of models, wrong sort, or unreadable
