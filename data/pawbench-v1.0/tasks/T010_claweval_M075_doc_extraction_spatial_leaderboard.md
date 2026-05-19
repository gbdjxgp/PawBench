---
id: M075_doc_extraction_spatial_leaderboard
name: Document Extraction - Spatial Reasoning Leaderboard
category: multimodal
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.5
  llm_judge: 0.5
workspace_files:
- source: assets/T010_claweval_M075_doc_extraction_spatial_leaderboard/fixtures/2512.17495v2.pdf
  dest: fixtures/2512.17495v2.pdf
labels:
  capabilities:
  - Tool_Use
  - Code_Manipulation
  - Planning
  - Self_Verification
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
- `fixtures/2512.17495v2.pdf` — the GroundingME paper

Build a unified **Spatial reasoning** leaderboard for **all open-source models** in the GroundingME paper:

1. From the **main experimental results table**, extract each open-source model's **Baseline** average Spatial score
2. From the **appendix table**, extract each open-source model's **Thinking** Spatial score
3. Merge both into one ranking, distinguishing entries by appending `(Base)` or `(Think)` to the model name
4. Sort all entries in **descending** order by Spatial score
5. Take **exactly the top 10** entries
6. Save them to `output/top10_os_spatial.csv` with **only two columns**: `Model_Condition,Score`
7. Generate a bar chart from this CSV at `output/top10_spatial_chart.png` (model names readable; bars in descending order; entries match top 10)

**Ground-truth top 10 (descending):**

| Rank | Model_Condition | Score |
|---|---|---|
| 1 | Qwen3-VL-A22B (Think) | 73.7 |
| 2 | Qwen3-VL-32B (Think) | 70.0 |
| 3 | Qwen3-VL-A3B (Think) | 53.3 |
| 4 | Qwen3-VL-A22B (Base) | 49.7 |
| 5 | Qwen3-VL-32B (Base) | 47.3 |
| 6 | GLM-4.5V (Think) | 45.3 |
| 7 | Qwen3-VL-8B (Think) | 43.0 |
| 8 | GLM-4.5V (Base) | 42.0 |
| 9 | Qwen2.5-VL-72B (Base) | 40.3 |
| 10 | Qwen2.5-VL-32B (Base) | 40.0 |

## Expected Behavior

- Read PDF
- Extract baseline Spatial scores from main table and Think Spatial scores from appendix
- Combine with `(Base)` / `(Think)` suffixes
- Sort descending; take top 10
- Save CSV with exactly 2 columns, 10 data rows + header
- Save bar chart PNG

## Grading Criteria

- [ ] Reads PDF (file_read)
- [ ] CSV exists (csv_exists)
- [ ] PNG exists (png_exists)
- [ ] CSV has exactly 2 columns (two_columns)
- [ ] CSV has 10 data rows (ten_rows)
- [ ] Top entries match (top_entries_present)
- [ ] Sorted descending (sorted_desc)
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
        "two_columns": 0.0,
        "ten_rows": 0.0,
        "top_entries_present": 0.0,
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

    csv_path = Path(workspace_path) / "output" / "top10_os_spatial.csv"
    png_path = Path(workspace_path) / "output" / "top10_spatial_chart.png"

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

    if re.search(r"GroundingME|Spatial|2512\.17495|appendix|main\s+table", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    lines = [ln for ln in csv_content.splitlines() if ln.strip()]
    if lines:
        first = lines[0]
        if first.count(",") == 1:
            result["two_columns"] = 1.0
        elif first.count(",") in (2, 3):
            result["two_columns"] = 0.4

        data_rows = len(lines) - 1 if lines else 0
        if data_rows == 10:
            result["ten_rows"] = 1.0
        elif 8 <= data_rows <= 12:
            result["ten_rows"] = 0.6

    targets = ["73.7", "70.0", "53.3", "49.7", "47.3", "45.3", "43.0", "42.0", "40.3", "40.0"]
    hits = sum(1 for v in targets if v in csv_content)
    if hits >= 7:
        result["top_entries_present"] = 1.0
    elif hits >= 4:
        result["top_entries_present"] = 0.6
    elif hits >= 2:
        result["top_entries_present"] = 0.3

    if csv_content:
        nums = [float(n) for n in re.findall(r"\d+\.\d+", csv_content) if 30 <= float(n) <= 90]
        if len(nums) >= 5:
            sorted_nums = sorted(nums, reverse=True)
            if nums[:len(sorted_nums)] == sorted_nums:
                result["sorted_desc"] = 1.0
            else:
                matches = sum(1 for a, b in zip(nums, sorted_nums) if a == b)
                result["sorted_desc"] = matches / len(sorted_nums) * 0.7

    return result
```

## LLM Judge Rubric

### Criterion 1: Data Accuracy & Strictness (Weight: 50%)

**Ground truth top 10 ranking (descending):**

| Rank | Model_Condition | Score |
|---|---|---|
| 1 | Qwen3-VL-A22B (Think) | 73.7 |
| 2 | Qwen3-VL-32B (Think) | 70.0 |
| 3 | Qwen3-VL-A3B (Think) | 53.3 |
| 4 | Qwen3-VL-A22B (Base) | 49.7 |
| 5 | Qwen3-VL-32B (Base) | 47.3 |
| 6 | GLM-4.5V (Think) | 45.3 |
| 7 | Qwen3-VL-8B (Think) | 43.0 |
| 8 | GLM-4.5V (Base) | 42.0 |
| 9 | Qwen2.5-VL-72B (Base) | 40.3 |
| 10 | Qwen2.5-VL-32B (Base) | 40.0 |

**Award:**
- **+1.0 — Data truncation & output strictness**: CSV has exactly 10 data rows + header; only 2 columns (`Model_Condition`, `Score`); order strictly matches the GT descending list; Base/Think conditions correctly merged; scores correctly extracted.
- 0 if wrong row count, wrong columns, wrong order, or incorrect values.

**Scoring bands:**
- **1.0**: Strictly correct
- **0.5–0.8**: Minor deviations
- **0.0–0.4**: Significant errors

### Criterion 2: Chart Execution (Weight: 50%)

Inspect `output/top10_spatial_chart.png`:

- Exactly 10 entries with bar heights approximately matching GT values
- Model names on axis fully legible (horizontal layout or rotated labels to avoid overlap)
- Bars in descending order
- Axis labels present

**Scoring bands:**
- **1.0**: All criteria met
- **0.5–0.8**: Minor issues (slight label overlap, slight order issue)
- **0.0–0.4**: Wrong count, unreadable labels, or wrong order
