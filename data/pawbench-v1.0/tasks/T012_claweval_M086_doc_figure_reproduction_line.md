---
id: M086_doc_figure_reproduction_line
name: Document Figure Reproduction - Line Chart
category: multimodal
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.1
  llm_judge: 0.9
workspace_files:
- source: assets/T012_claweval_M086_doc_figure_reproduction_line/fixtures/2512.17495v2.pdf
  dest: fixtures/2512.17495v2.pdf
labels:
  capabilities:
  - Code_Manipulation
  - Tool_Use
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

The workspace contains:
- `fixtures/2512.17495v2.pdf` — the GroundingME paper

You are preparing a presentation on the GroundingME benchmark and need to **accurately recreate** its fine-tuning performance chart.

Steps:
1. Locate **Figure 6** in the paper:
   *"Out-of-domain performance of fine-tuned Qwen3-VL-8B-Instruct"* — a line chart with markers
2. Write a Python script `output/reproduce_fig6.py` that fully reconstructs this chart procedurally using **matplotlib** (or plotly/seaborn). **Do not** simply extract the image from the PDF — the chart must be drawn from scratch.
3. The chart must include:
   - **5 SFT data ratios** on the x-axis: `1:8, 1:4, 1:2, 1:1, 2:1`
   - **Two lines** with markers: `GroundingME w/o Rej.` and `Rejection Category`
   - **Two horizontal dashed baselines** at `y=38.8` and `y=0`
   - **Numerical annotations** on each data point (e.g., 32.8, 27.9)
   - **Legend** identifying lines and baselines
   - **X-axis label**: `SFT Data Ratio (Negative to Positive)`
   - **Y-axis label**: `ACC@0.5`
4. Execute the script and save the image as `output/figure6_reproduce.png`

## Expected Behavior

- Read PDF, find Figure 6
- Author a Python script using matplotlib (or plotly/seaborn) that reconstructs the line chart procedurally
- Run the script; produce the PNG
- Both files (`reproduce_fig6.py` and `figure6_reproduce.png`) must be in `output/`

## Grading Criteria

- [ ] Reads PDF (file_read)
- [ ] Script exists (script_exists)
- [ ] PNG exists (png_exists)
- [ ] Script uses plotting library (uses_plotting)
- [ ] Script does NOT use PDF image extraction (no_extraction)
- [ ] Script references key elements (data_ratios, baselines, labels) (script_complete)
- [ ] PNG substantial (png_substantial)

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_read": 0.0,
        "script_exists": 0.0,
        "png_exists": 0.0,
        "uses_plotting": 0.0,
        "no_extraction": 1.0,
        "script_complete": 0.0,
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

    script_path = Path(workspace_path) / "output" / "reproduce_fig6.py"
    png_path = Path(workspace_path) / "output" / "figure6_reproduce.png"

    script_content = ""
    if script_path.is_file():
        result["script_exists"] = 1.0
        try:
            script_content = script_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    if png_path.is_file():
        result["png_exists"] = 1.0
        try:
            size = png_path.stat().st_size
            if size > 8000:
                result["png_substantial"] = 1.0
            elif size > 3000:
                result["png_substantial"] = 0.5
        except Exception:
            pass

    combined = transcript_text + " " + script_content

    if re.search(r"GroundingME|2512\.17495|Figure\s*6|fine-?tun", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    if re.search(r"matplotlib|pyplot|plotly|seaborn", script_content, re.IGNORECASE):
        result["uses_plotting"] = 1.0

    if re.search(r"fitz.{0,40}get_pixmap|pdf2image|extract_image|pypdf.{0,40}extract|PyPDF2|pdfplumber.*image", script_content, re.IGNORECASE):
        result["no_extraction"] = 0.0

    sub_signals = [
        bool(re.search(r"1\s*:\s*8|1:4|1:2|1:1|2:1", script_content)),
        bool(re.search(r"plot|line|marker", script_content, re.IGNORECASE)),
        bool(re.search(r"38\.8|baseline", script_content, re.IGNORECASE)),
        bool(re.search(r"axhline|hlines|--|dashed|linestyle", script_content, re.IGNORECASE)),
        bool(re.search(r"legend|annotate", script_content, re.IGNORECASE)),
        bool(re.search(r"ACC.{0,5}0\.5|SFT|Negative.{0,3}Positive", script_content, re.IGNORECASE)),
    ]
    score = sum(sub_signals) / len(sub_signals)
    result["script_complete"] = score

    return result
```

## LLM Judge Rubric

### Criterion: Visual Fidelity vs. Reference Figure 6 (Weight: 100%)

Compare the candidate reproduction (`output/figure6_reproduce.png`) against Figure 6 of the GroundingME paper.

**Base score: 1.0**, with deductions (minimum 0.0):

- **−0.34 — Data errors or missing layout**: chart is not a line chart with markers; missing the 5 SFT data ratios (1:8, 1:4, 1:2, 1:1, 2:1); values for the two lines (`GroundingME w/o Rej.` and `Rejection Category`) incorrect or missing.
- **−0.33 — Inaccurate baselines or annotations**: missing the two horizontal dashed baselines (y=38.8, y=0); baselines not dashed; data-point numerical annotations (e.g., 32.8, 27.9) absent.
- **−0.33 — Incorrect labels, legend, or axes**: legend missing/incomplete (must cover lines + baselines); x-axis label `SFT Data Ratio (Negative to Positive)` missing/incorrect; y-axis label `ACC@0.5` missing/incorrect; colors drastically lack visual distinction.

Also apply a **0** if the candidate `reproduce_fig6.py` extracts the figure image from the PDF directly (e.g., uses `fitz.get_pixmap`, `pdf2image`, or `extract_image`) rather than reconstructing it procedurally.

**Scoring bands:**
- **0.7–1.0**: Highly faithful reconstruction
- **0.4–0.7**: Recognizable line chart with most elements but multiple deductions
- **0.0–0.3**: Wrong chart type, severe issues, or extracted from PDF
