---
id: M005_score_canon
name: Sheet Music Reproduction - Canon in D
category: multimodal
grading_type: hybrid
timeout_seconds: 1200
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T001_claweval_M005_score_canon/fixtures/Canon1.png
  dest: fixtures/Canon1.png
labels:
  capabilities:
  - Tool_Use
  - Code_Manipulation
  - Logic_Reasoning
  modality:
    type: multimodal
    channels:
    - image
  scenario: Content_Creation/Design
  complexity: L3
  environment: closed
---
## Prompt

The workspace contains a sheet music image of **Canon in D** by Johann Pachelbel:
- `fixtures/Canon1.png`

Please first view the image, then generate `output/output.html` reproducing the score using **inline SVG** with the following requirements:

1. Include the title (`Canon in D`), composer (`Johann Pachelbel`), tempo (`quarter = 100`)
2. Draw two staves: **treble clef** on top, **bass clef** on bottom, joined by a brace
3. Display the correct **key signature** (D Major: 2 sharps — F#, C#) and **time signature** (4/4)
4. Reproduce **8 measures** total, in two lines of 4 measures each:
   - **Measures 1–4** (line 1): treble has whole rests; bass plays eighth-note pairs (arpeggios)
     - M1 (D-A): D3,F#3 / A3,D4 / A2,C#3 / E3,A3
     - M2 (Bm-F#m): B2,D3 / F#3,B3 / F#2,A2 / C#3,F#3
     - M3 (G-D): G2,B2 / D3,G3 / D3,F#3 / A3,D4
     - M4 (G-A): G2,B2 / D3,G3 / A2,C#3 / E3,A3
   - **Measures 5–8** (line 2): bass repeats the same ostinato; treble enters with half notes (2 beats each)
     - M5: F#5 / E5
     - M6: D5 / C#5
     - M7: B4 / A4
     - M8: B4 / C#5
5. Include barlines, stems, beams, dynamic markings (`p` at M1, `m` / `mf` at M5, crescendo near M4)
6. The bass arpeggio pattern **must vary per measure** (different note heights) — not a flat repeated pattern

Save the result to `output/output.html` (a self-contained HTML file with inline SVG).

## Expected Behavior

- Read the reference image `fixtures/Canon1.png`
- Analyze the staff structure and notes
- Construct a single HTML file with inline SVG drawing all 8 measures
- Treble staff in M1–4 should be empty (whole rests)
- Treble melody in M5–8 should descend then rise: F#5→E5→D5→C#5→B4→A4→B4→C#5
- Save to `output/output.html`

## Grading Criteria

- [ ] Reads the reference PNG (file_read)
- [ ] Output HTML exists and contains inline SVG (output_file_exists, has_svg)
- [ ] Title and composer text present (metadata_present)
- [ ] Treble & bass clefs and 4/4 time, 2 sharps (key_time_clefs)
- [ ] 8 measures organized in 2 lines (measures_count)
- [ ] Bass arpeggio note positions vary across measures (bass_varies)
- [ ] Treble M5–8 melody pitch labels appear (melody_pitches)
- [ ] Reasonable file size (>4KB) (substantial_output)

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_read": 0.0,
        "output_file_exists": 0.0,
        "has_svg": 0.0,
        "metadata_present": 0.0,
        "key_time_clefs": 0.0,
        "measures_count": 0.0,
        "bass_varies": 0.0,
        "melody_pitches": 0.0,
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
            if len(file_content) > 4000:
                result["substantial_output"] = 1.0
            elif len(file_content) > 1500:
                result["substantial_output"] = 0.5
        except Exception:
            pass

    combined = transcript_text + " " + file_content

    if re.search(r"Canon1\.png|read_image|view_image|fixtures/Canon", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    if re.search(r"<svg\b", file_content, re.IGNORECASE):
        result["has_svg"] = 1.0

    has_title = bool(re.search(r"Canon\s*in\s*D", file_content, re.IGNORECASE))
    has_composer = bool(re.search(r"Pachelbel", file_content, re.IGNORECASE))
    if has_title and has_composer:
        result["metadata_present"] = 1.0
    elif has_title or has_composer:
        result["metadata_present"] = 0.5

    has_treble = bool(re.search(r"treble|G\s*clef|𝄞", file_content, re.IGNORECASE))
    has_bass = bool(re.search(r"bass|F\s*clef|𝄢", file_content, re.IGNORECASE))
    has_44 = bool(re.search(r"4/4|time.{0,30}(?:4|four)", file_content, re.IGNORECASE))
    has_sharps = bool(re.search(r"2\s*sharps|F#|C#|♯|sharp", file_content, re.IGNORECASE))
    score = sum([has_treble, has_bass, has_44, has_sharps]) / 4
    result["key_time_clefs"] = score

    measure_signals = re.findall(r"measure|barline|m1|m2|m3|m4|m5|m6|m7|m8", file_content, re.IGNORECASE)
    if len(measure_signals) >= 8:
        result["measures_count"] = 1.0
    elif len(measure_signals) >= 4:
        result["measures_count"] = 0.5

    bass_pitches = set(re.findall(r"\b[A-G][#b]?[2-4]\b", file_content))
    distinctive = {"D3", "F#3", "A3", "B2", "G2", "C#3", "E3"}
    overlap = bass_pitches & distinctive
    if len(overlap) >= 4:
        result["bass_varies"] = 1.0
    elif len(overlap) >= 2:
        result["bass_varies"] = 0.5

    melody_pitches = set(re.findall(r"\b[A-G][#b]?[4-5]\b", file_content))
    melody_target = {"F#5", "E5", "D5", "C#5", "B4", "A4"}
    overlap_m = melody_pitches & melody_target
    if len(overlap_m) >= 4:
        result["melody_pitches"] = 1.0
    elif len(overlap_m) >= 2:
        result["melody_pitches"] = 0.5

    return result
```

## LLM Judge Rubric

### Criterion 1: Note Accuracy (Weight: 50%)

Inspect the generated `output/output.html` SVG content (referencing the reference Canon in D image where helpful):

**Reference content:**
- Title: `Canon in D`, Composer: `Johann Pachelbel`, Tempo: `quarter = 100`
- Key: D Major (2 sharps: F# and C#), Time: 4/4
- Two staves: treble clef (top) + bass clef (bottom), joined by a brace
- 8 measures total in two lines of 4 measures each

**LINE 1 — Measures 1–4 (bass solo, treble rests):**
- Treble: whole rests in ALL of M1–M4
- Bass: 8 eighth notes per measure (pairs of 2). The arpeggio pattern is:
  - M1 (D-A): D3,F#3 / A3,D4 / A2,C#3 / E3,A3
  - M2 (Bm-F#m): B2,D3 / F#3,B3 / F#2,A2 / C#3,F#3
  - M3 (G-D): G2,B2 / D3,G3 / D3,F#3 / A3,D4
  - M4 (G-A): G2,B2 / D3,G3 / A2,C#3 / E3,A3
- Dynamic: `p` at M1, crescendo near end of M4

**LINE 2 — Measures 5–8 (melody enters):**
- Bass: repeats the same ostinato as M1–M4
- Treble: half notes (2 beats each) — F#5, E5, D5, C#5, B4, A4, B4, C#5
- Dynamic: `m` (mf) at M5

**KEY FEATURES to verify:**
1. Treble must be empty (rests) in M1–4
2. Bass eighth-note pairs should show clear UP-DOWN arpeggio motion, not a flat repeated pattern
3. Each measure's bass notes should be at different heights (D-A, Bm-F#m, G-D, G-A progressions)
4. Treble in M5–8 must descend then rise: F#5→E5→D5→C#5→B4→A4→B4→C#5

**Scoring bands:**
- **0.0–0.2**: Bass is a flat repeated pattern OR treble is not resting in M1–4
- **0.2–0.4**: Some measures show different bass shapes but melody is wrong
- **0.4–0.7**: General contour is right but specific pitches are off
- **0.7–1.0**: Bass arpeggio varies correctly per measure AND melody descends then rises with correct pitches

### Criterion 2: Layout & Notation Quality (Weight: 25%)

- Correct key signature (2 sharps), time signature (4/4), clefs (G + F)
- Title, composer, tempo marking visible
- Two clean lines of 4 measures each
- Barlines, stems, beams visible
- Dynamics markings (`p`, `m`/`mf`)

**Scoring bands:**
- **1.0**: All notation elements correctly present and visually clean
- **0.6–0.8**: Most elements present, minor issues
- **0.3–0.5**: Significant notation elements missing
- **0.0–0.2**: Bare or unrecognizable as sheet music

### Criterion 3: Overall Visual Match (Weight: 25%)

How well does the SVG sheet music resemble the reference Canon image overall? Consider proportions, staff layout, brace, and general musical typesetting quality.

**Scoring bands:**
- **0.7–1.0**: Closely matches reference layout
- **0.4–0.7**: Recognizable but with significant differences
- **0.0–0.4**: Bears little resemblance
