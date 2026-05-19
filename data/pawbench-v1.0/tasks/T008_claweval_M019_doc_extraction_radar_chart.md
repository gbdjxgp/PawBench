---
id: M019_doc_extraction_radar_chart
name: Document Extraction - Radar Chart from PDF
category: multimodal
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.4
  llm_judge: 0.6
workspace_files:
- source: assets/T008_claweval_M019_doc_extraction_radar_chart/fixtures/GroundingME.pdf
  dest: fixtures/GroundingME.pdf
labels:
  capabilities:
  - Tool_Use
  - Code_Manipulation
  - Planning
  modality:
    type: multimodal
    channels:
    - image
  scenario: Data_Analytics/Visualization
  complexity: L3
  environment: closed
---
## Prompt

The workspace contains the file:
- `fixtures/GroundingME.pdf` — a research paper

Steps:
1. Read the PDF and locate the **main experimental results table**
2. Extract the **average scores** of the **four L-1 dimensions** and the **Total** score for two models:
   - **Qwen3-VL-A22B**
   - **Gemini-2.5-Pro**
3. Save the data to `output/model_comparison.csv` with columns:
   `model, dim1, dim2, dim3, dim4, total`
4. Create a **radar chart** comparing the two models on the 4 L-1 dimensions:
   - Axes range: 0 → 100
   - Legend identifying both models
   - Colors: **blue** for Qwen3-VL-A22B, **red** for Gemini-2.5-Pro
   - Save the chart as `output/comparison_radar.png`

**Ground-truth values** (must appear in your CSV):
| Model | Dim1 | Dim2 | Dim3 | Dim4 | Total |
|---|---|---|---|---|---|
| Qwen3-VL-A22B | 69.6 | 49.7 | 54.0 | 0.0 | 45.1 |
| Gemini-2.5-Pro | 34.8 | 34.0 | 7.0 | 7.0 | 20.7 |

(You should derive these from the PDF, but they are listed for verification.)

Save both files in `output/`.

## Expected Behavior

- Read PDF text/tables
- Extract the values for the two models
- Write `output/model_comparison.csv`
- Generate `output/comparison_radar.png` using matplotlib (or similar) — radar/spider chart
- Use blue for Qwen3 and red for Gemini

## Grading Criteria

- [ ] Reads PDF (file_read)
- [ ] CSV file exists (csv_exists)
- [ ] PNG file exists (png_exists)
- [ ] CSV mentions both models (csv_models)
- [ ] CSV contains correct values for Qwen (qwen_values)
- [ ] CSV contains correct values for Gemini (gemini_values)
- [ ] Radar chart generated (chart_generated)
- [ ] Substantial PNG (>5KB) (png_substantial)

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_read": 0.0,
        "csv_exists": 0.0,
        "png_exists": 0.0,
        "csv_models": 0.0,
        "qwen_values": 0.0,
        "gemini_values": 0.0,
        "chart_generated": 0.0,
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

    csv_path = Path(workspace_path) / "output" / "model_comparison.csv"
    png_path = Path(workspace_path) / "output" / "comparison_radar.png"

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

    if re.search(r"GroundingME|\.pdf|extract.{0,20}pdf", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    has_qwen = bool(re.search(r"Qwen3.{0,5}VL|Qwen-?3", csv_content, re.IGNORECASE))
    has_gemini = bool(re.search(r"Gemini.{0,5}2\.5|Gemini-?2", csv_content, re.IGNORECASE))
    if has_qwen and has_gemini:
        result["csv_models"] = 1.0
    elif has_qwen or has_gemini:
        result["csv_models"] = 0.5

    qwen_targets = ["69.6", "49.7", "54.0", "45.1"]
    qwen_hits = sum(1 for v in qwen_targets if v in csv_content)
    if qwen_hits >= 3:
        result["qwen_values"] = 1.0
    elif qwen_hits >= 2:
        result["qwen_values"] = 0.6
    elif qwen_hits >= 1:
        result["qwen_values"] = 0.3

    gemini_targets = ["34.8", "34.0", "20.7"]
    gemini_hits = sum(1 for v in gemini_targets if v in csv_content)
    if gemini_hits >= 2:
        result["gemini_values"] = 1.0
    elif gemini_hits >= 1:
        result["gemini_values"] = 0.5

    chart_signals = bool(re.search(r"radar|polar|spider|matplotlib|pyplot|plotly", combined, re.IGNORECASE))
    if chart_signals and result["png_exists"]:
        result["chart_generated"] = 1.0
    elif result["png_exists"]:
        result["chart_generated"] = 0.6
    elif chart_signals:
        result["chart_generated"] = 0.3

    return result
```

## LLM Judge Rubric

### Criterion 1: Data Accuracy (Weight: 40%)

Inspect `output/model_comparison.csv`. Ground-truth values:

| Model | Dim1 | Dim2 | Dim3 | Dim4 | Total |
|---|---|---|---|---|---|
| Qwen3-VL-A22B | 69.6 | 49.7 | 54.0 | 0.0 | 45.1 |
| Gemini-2.5-Pro | 34.8 | 34.0 | 7.0 | 7.0 | 20.7 |

**Scoring bands:**
- **1.0**: All values match exactly
- **0.7–0.9**: Minor discrepancies (rounding within ±0.5)
- **0.3–0.6**: Some correct, others significantly wrong
- **0.0–0.2**: Mostly incorrect

### Criterion 2: Chart Quality (Weight: 60%)

Inspect the radar-chart PNG (`output/comparison_radar.png`) — review either the file content or the code/script used to generate it:

**Chart specifications (~67% of this criterion):**
- Must be a radar (spider/web) chart
- Exactly 4 L-1 dimensions (excluding Total)
- Axis range 0 → 100
- Legend identifying both models
- Color mapping: blue for Qwen3, red for Gemini
- Data points match the ground truth values

**Aesthetic quality (~33%):**
- No overlapping text/fonts
- Labels readable on all axes
- No incomplete layers or misaligned elements
- Clean, professional appearance

**Scoring bands:**
- **1.0**: All specs met + clean visualization
- **0.6–0.9**: Most specs met, minor visual issues
- **0.3–0.6**: Recognizable as radar but with significant flaws (wrong colors, missing legend)
- **0.0–0.3**: Wrong chart type or no chart
