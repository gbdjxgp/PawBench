---
id: M077_doc_extraction_cross_modality
name: Document Extraction - LLaVA-OneVision Cross-Modality
category: multimodal
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.67
  llm_judge: 0.33
labels:
  capabilities:
  - Tool_Use
  - Code_Manipulation
  - Math_Computation
  - Planning
  modality:
    type: multimodal
    channels:
    - image
  scenario: Data_Analytics/Visualization
  complexity: L3
  environment: open
---
## Prompt

You are a researcher studying how **LLaVA-OneVision** performs across single-image, multi-image, and video scenarios. From the paper **"LLaVA-OneVision: Easy Visual Task Transfer"**, you need to merge data from **Table 3** (single-image benchmarks) and **Table 5** (video benchmarks) to compare models across both modalities.

Steps:
1. From **Table 3** (single-image), extract each model's scores on:
   `AI2D (test), ChartQA (test), DocVQA (test), MathVista (testmini), MMMU (val), MMVet (test)`
2. From **Table 5** (video), extract each model's scores on:
   `ActivityNet-QA (test), EgoSchema (test), MLVU (m-avg), MVBench (test), PerceptionTest (val), VideoMME (wo subs)`
3. Join by model name. Include all LLaVA-OneVision variants (0.5B, 7B, 72B, both SI and final) **and** GPT-4V — 7 rows total
4. Compute `Average_Single_Image` (mean of the 6 single-image metrics, skip missing) and `Average_Video` (mean of the 6 video metrics, skip missing)
5. Sort by `Average_Video` **descending**
6. Save as `output/llava_ov_cross_modality.csv` with columns:
   `Model, AI2D, ChartQA, DocVQA, MathVista, MMMU, MMVet, ActivityNetQA, EgoSchema, MLVU, MVBench, PerceptionTest, VideoMME, Average_Single_Image, Average_Video` (15 columns)
7. Generate `output/llava_ov_cross_modality_chart.png` — a **scatter plot** with `Average_Single_Image` on the x-axis and `Average_Video` on the y-axis. Label each point with the model name. Add a diagonal `y = x` reference line.

**Ground-truth values (sorted by Average_Video descending):**

| Model | AI2D | ChartQA | DocVQA | MathVista | MMMU | MMVet | ActNetQA | EgoSchema | MLVU | MVBench | PercepTest | VideoMME | Avg_SI | Avg_Video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LLaVA-OV-72B | 85.6 | 83.7 | 91.3 | 67.5 | 56.8 | 63.7 | 62.3 | 62.0 | 68.0 | 59.4 | 66.9 | 66.2 | 74.77 | 64.13 |
| LLaVA-OV-72B (SI) | 85.1 | 84.9 | 91.8 | 66.5 | 57.4 | 60.0 | 62.1 | 58.6 | 60.9 | 57.1 | 62.3 | 64.8 | 74.28 | 60.97 |
| LLaVA-OV-7B | 81.4 | 80.0 | 87.5 | 63.2 | 48.8 | 57.5 | 56.6 | 60.1 | 64.7 | 56.7 | 57.1 | 58.2 | 69.73 | 58.90 |
| LLaVA-OV-7B (SI) | 81.6 | 78.8 | 86.9 | 56.1 | 47.3 | 58.8 | 55.1 | 52.9 | 60.2 | 51.2 | 54.9 | 55.0 | 68.25 | 54.88 |
| GPT-4V | 78.2 | 78.5 | 88.4 | 49.9 | 56.8 | 49.9 | 57.0 | – | 49.2 | 43.5 | – | 59.9 | 66.95 | 52.40 |
| LLaVA-OV-0.5B | 57.1 | 61.4 | 70.0 | 34.8 | 31.4 | 29.1 | 50.5 | 26.8 | 50.3 | 45.5 | 49.2 | 44.0 | 47.30 | 44.38 |
| LLaVA-OV-0.5B (SI) | 54.2 | 61.0 | 71.2 | 34.6 | 31.2 | 26.9 | 49.0 | 33.1 | 47.9 | 43.3 | 48.6 | 41.7 | 46.52 | 43.93 |

GPT-4V averages computed over available values only (skip missing `–`).

## Expected Behavior

- Identify the LLaVA-OneVision paper (e.g., search ArXiv) and read it
- Extract Tables 3 & 5 cross-modality benchmarks for the 7 specified models
- Compute averages, sort, save CSV (15 columns) and scatter plot

## Grading Criteria

- [ ] Searched/read paper (file_or_search)
- [ ] CSV exists (csv_exists)
- [ ] PNG exists (png_exists)
- [ ] All 15 columns (columns_complete)
- [ ] All 7 models present (models_complete)
- [ ] Average_Video values approximately correct (averages_correct)
- [ ] Sorted descending by Average_Video (sorted_desc)
- [ ] PNG substantial (png_substantial)

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_or_search": 0.0,
        "csv_exists": 0.0,
        "png_exists": 0.0,
        "columns_complete": 0.0,
        "models_complete": 0.0,
        "averages_correct": 0.0,
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

    csv_path = Path(workspace_path) / "output" / "llava_ov_cross_modality.csv"
    png_path = Path(workspace_path) / "output" / "llava_ov_cross_modality_chart.png"

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

    if re.search(r"LLaVA.{0,10}OneVision|llava-?ov|easy.{0,5}visual.{0,5}task.{0,5}transfer|search|arxiv", combined, re.IGNORECASE):
        result["file_or_search"] = 1.0

    required_cols = ["AI2D", "ChartQA", "DocVQA", "MathVista", "MMMU", "MMVet", "ActivityNet", "EgoSchema", "MLVU", "MVBench", "Perception", "VideoMME", "Average_Single_Image", "Average_Video"]
    found_cols = sum(1 for c in required_cols if re.search(re.escape(c).replace(r"\_", "[_-]?"), csv_content, re.IGNORECASE))
    if found_cols >= 12:
        result["columns_complete"] = 1.0
    elif found_cols >= 8:
        result["columns_complete"] = 0.6
    elif found_cols >= 4:
        result["columns_complete"] = 0.3

    models = ["LLaVA-OV-72B", "LLaVA-OV-7B", "LLaVA-OV-0.5B", "GPT-4V"]
    found_models = sum(1 for m in models if re.search(re.escape(m).replace("-", "[-_ ]?"), csv_content, re.IGNORECASE))
    if found_models >= 4:
        result["models_complete"] = 1.0
    elif found_models >= 2:
        result["models_complete"] = 0.5

    avg_video_targets = ["64.13", "60.97", "58.90", "54.88", "52.40", "44.38", "43.93"]
    hits = sum(1 for v in avg_video_targets if v in csv_content)
    if hits >= 5:
        result["averages_correct"] = 1.0
    elif hits >= 3:
        result["averages_correct"] = 0.6
    elif hits >= 1:
        result["averages_correct"] = 0.3

    if csv_content:
        nums = [float(n) for n in re.findall(r"\d+\.\d{1,2}", csv_content) if 40 <= float(n) <= 75]
        target_set = {64.13, 60.97, 58.90, 54.88, 52.40, 44.38, 43.93}
        candidate = []
        for n in nums:
            for t in target_set:
                if abs(n - t) < 0.05:
                    candidate.append(t)
                    break
        if len(candidate) >= 4:
            sorted_check = candidate == sorted(candidate, reverse=True)
            if sorted_check:
                result["sorted_desc"] = 1.0
            else:
                result["sorted_desc"] = 0.3

    return result
```

## LLM Judge Rubric

### Criterion 1: Data Accuracy & File Compliance (Weight: 67%)

**Ground truth (sorted by Average_Video descending):**

| Model | Avg_SI | Avg_Video |
|---|---|---|
| LLaVA-OV-72B | 74.77 | 64.13 |
| LLaVA-OV-72B (SI) | 74.28 | 60.97 |
| LLaVA-OV-7B | 69.73 | 58.90 |
| LLaVA-OV-7B (SI) | 68.25 | 54.88 |
| GPT-4V | 66.95 | 52.40* |
| LLaVA-OV-0.5B | 47.30 | 44.38 |
| LLaVA-OV-0.5B (SI) | 46.52 | 43.93 |

*GPT-4V averages computed over available values only (skip missing).

**Award:**
- **+0.5 — Data accuracy**: CSV contains the 7 models with correct scores; averages correctly computed (mean of available values); sort by Average_Video correct; GPT-4V missing values handled correctly.
- **+0.5 — File compliance**: All 15 required columns present; well-formed with comma delimiter; missing values marked.

**Scoring bands:**
- **1.0**: Both awarded
- **0.5**: One awarded
- **0.0**: Neither

### Criterion 2: Chart Correctness & Aesthetics (Weight: 33%)

Inspect `output/llava_ov_cross_modality_chart.png`:

- Scatter plot (NOT bar or line)
- X-axis: Average_Single_Image; Y-axis: Average_Video
- Each point labeled with model name
- Diagonal `y = x` reference line present
- 7 data points approximately matching GT positions
- Labels readable; axes labeled

**Scoring bands:**
- **1.0**: All criteria met
- **0.5–0.8**: Minor issues (labels overlap, missing diagonal)
- **0.0–0.4**: Wrong chart type, missing reference line, or unreadable
