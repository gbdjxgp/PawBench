---
id: M008_metro_map_1
name: NYC Subway Map Reproduction
category: multimodal
grading_type: hybrid
timeout_seconds: 1200
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T004_claweval_M008_metro_map_1/fixtures/metro1.png
  dest: fixtures/metro1.png
labels:
  capabilities:
  - Tool_Use
  - Code_Manipulation
  modality:
    type: multimodal
    channels:
    - image
  scenario: Content_Creation/Design
  complexity: L3
  environment: closed
---
## Prompt

The workspace contains a reference subway-map image:
- `fixtures/metro1.png` — the **southern portion of the New York City subway map**, covering lower Manhattan and Brooklyn

Please first view the image, then generate `output/output.html` reproducing this metro map using **inline SVG**:

1. Render the major NYC subway lines with **correct colors**:
   - Lines 1/2/3 — RED (west side / 7th Ave)
   - Lines 4/5/6 — GREEN (east side / Lexington Ave)
   - Lines A/C/E — BLUE (8th Ave)
   - Lines N/Q/R — YELLOW (Broadway)
   - Lines D/F — ORANGE (6th Ave)
   - Lines J/M/Z — BROWN (Williamsburg Bridge)
   - Line G — LIGHT GREEN (Brooklyn only)
   - Line 7 — PURPLE (top, to Queens)
   - PATH trains — dashed lines to New Jersey
2. Label key transfer hubs and stations:
   - West 4 St / Washington Sq, Canal St, Fulton St, Brooklyn Bridge / Chambers St, WTC, Atlantic Av, Borough Hall, Court St, Jay St MetroTech, South Ferry / Whitehall St, Battery Park area
3. Layout: **Manhattan on the LEFT**, **Brooklyn on the RIGHT**, separated by the East River; lines crossing the river via bridges/tunnels
4. Background a grayish-blue with `Brooklyn` in large text on the right side
5. Show transfer stations with multi-line markers; ensure station labels are legible

Save the result to `output/output.html` (a self-contained HTML file with inline SVG).

## Expected Behavior

- Read `fixtures/metro1.png`
- Build inline SVG with colored polylines for each subway line, with circles/squares for stations
- Add text labels for stations and `Brooklyn` background label
- Save to `output/output.html`

## Grading Criteria

- [ ] Reads reference PNG (file_read)
- [ ] Output HTML exists with inline SVG (output_file_exists, has_svg)
- [ ] Major line colors present (line_colors)
- [ ] Key station labels present (stations_labeled)
- [ ] Manhattan/Brooklyn layout indicated (layout_correct)
- [ ] Substantial output (>5KB) (substantial_output)

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_read": 0.0,
        "output_file_exists": 0.0,
        "has_svg": 0.0,
        "line_colors": 0.0,
        "stations_labeled": 0.0,
        "layout_correct": 0.0,
        "substantial_output": 0.0,
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

    output_path = Path(workspace_path) / "output" / "output.html"
    file_content = ""
    if output_path.is_file():
        result["output_file_exists"] = 1.0
        try:
            file_content = output_path.read_text(encoding="utf-8", errors="ignore")
            if len(file_content) > 5000:
                result["substantial_output"] = 1.0
            elif len(file_content) > 1500:
                result["substantial_output"] = 0.5
        except Exception:
            pass

    combined = transcript_text + " " + file_content

    if re.search(r"metro1\.png|地铁|read_image|view_image|fixtures/metro", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    if re.search(r"<svg\b", file_content, re.IGNORECASE):
        result["has_svg"] = 1.0

    color_signals = []
    color_signals.append(bool(re.search(r"red|#(?:ee|ff|e[0-9a-f])[0-2][0-2][0-2][0-2]|#[ef][0-9a-f]0000", file_content, re.IGNORECASE)))
    color_signals.append(bool(re.search(r"green|#0?0[a-f0-9][0-2]00|#[0-2]e[0-3]", file_content, re.IGNORECASE)))
    color_signals.append(bool(re.search(r"blue|#0[0-9a-f]{2}[a-f][a-f0-9]|#[0-2][0-2][0-2][a-f][a-f0-9]", file_content, re.IGNORECASE)))
    color_signals.append(bool(re.search(r"yellow|#[ef][ef][a-f0-9]{2}0[0-2]|#ff[a-f0-9]{2}00", file_content, re.IGNORECASE)))
    color_signals.append(bool(re.search(r"orange|#[ef][a-f0-9]{2}[5-9][0-9a-f]00", file_content, re.IGNORECASE)))
    color_signals.append(bool(re.search(r"brown|#[68-9a-f][2-5][0-2][0-2]", file_content, re.IGNORECASE)))
    color_signals.append(bool(re.search(r"purple|violet", file_content, re.IGNORECASE)))
    color_count = sum(color_signals)
    if color_count >= 5:
        result["line_colors"] = 1.0
    elif color_count >= 3:
        result["line_colors"] = 0.6
    elif color_count >= 1:
        result["line_colors"] = 0.3

    stations = ["Canal", "Fulton", "Brooklyn Bridge", "WTC", "Atlantic", "West 4", "Borough Hall", "Whitehall", "Battery", "Chambers", "MetroTech", "South Ferry"]
    found_stations = sum(1 for s in stations if re.search(re.escape(s), file_content, re.IGNORECASE))
    if found_stations >= 6:
        result["stations_labeled"] = 1.0
    elif found_stations >= 3:
        result["stations_labeled"] = 0.6
    elif found_stations >= 1:
        result["stations_labeled"] = 0.3

    has_brooklyn = bool(re.search(r"Brooklyn", file_content, re.IGNORECASE))
    has_manhattan = bool(re.search(r"Manhattan", file_content, re.IGNORECASE))
    has_river = bool(re.search(r"East River|river", file_content, re.IGNORECASE))
    layout_count = sum([has_brooklyn, has_manhattan, has_river])
    if layout_count >= 2:
        result["layout_correct"] = 1.0
    elif layout_count >= 1:
        result["layout_correct"] = 0.5

    return result
```

## LLM Judge Rubric

### Criterion 1: Subway Lines & Colors (Weight: 30%)

**Reference content:**
- Lines 1/2/3 — RED (west side, 7th Ave) running through Chambers St to Brooklyn
- Lines 4/5/6 — GREEN (east side, Lexington) through Brooklyn Bridge to Brooklyn
- Lines A/C/E — BLUE (8th Ave) through West 4 St, down to WTC/Fulton St
- Lines N/Q/R — YELLOW through Canal St, City Hall
- Lines D/F — ORANGE through West 4 St, Broadway-Lafayette
- Lines J/M/Z — BROWN along Williamsburg Bridge to Brooklyn
- Line G — LIGHT GREEN, Brooklyn only
- Line 7 — PURPLE at the top connecting to Queens
- PATH — dashed lines to New Jersey

**Scoring bands:**
- **1.0**: 5+ lines with correct colors
- **0.6–0.8**: 3–4 lines with mostly correct colors
- **0.3–0.5**: A few lines, colors mostly wrong
- **0.0–0.2**: Few or no recognizable subway lines

### Criterion 2: Stations & Layout (Weight: 40%)

**Key stations and landmarks:**
- West 4 St / Washington Sq — major transfer hub (A/C/E/D/F meet)
- Canal St — multiple lines cross
- Fulton St — major hub in Financial District
- Brooklyn Bridge / Chambers St — 4/5/6 cross East River
- WTC (World Trade Center) — PATH and E
- Atlantic Av — major Brooklyn hub (many lines converge)
- Borough Hall, Court St, Jay St MetroTech — Brooklyn downtown
- South Ferry / Whitehall St — southern tip of Manhattan
- Battery Park — bottom-left of Manhattan

**Layout:**
- Manhattan on the LEFT, Brooklyn on the RIGHT
- East River separates them; lines cross via bridges/tunnels
- Background grayish-blue, with `Brooklyn` labeled in large text

**Scoring bands:**
- **0.7–1.0**: Most key stations labeled correctly + correct geographic layout
- **0.4–0.7**: Some stations + roughly correct layout
- **0.1–0.4**: Few stations, layout inaccurate
- **0.0**: No recognizable stations

### Criterion 3: Topology & Transfer Markers (Weight: 20%)

- Transfer stations indicated (multi-line markers / shared circles)
- Lines connect at correct stations (e.g., A/C/E/D/F at West 4)
- Visual consistency in line spacing

**Scoring bands:**
- **1.0**: Topology correct, transfers visible
- **0.5–0.8**: Mostly correct
- **0.0–0.4**: Topology incorrect

### Criterion 4: Cleanliness & Legibility (Weight: 10%)

- Station names legible
- Lines don't overlap chaotically
- Overall visual quality

**Scoring bands:**
- **1.0**: Clean, legible map
- **0.5–0.8**: Mostly legible
- **0.0–0.4**: Cluttered or illegible
