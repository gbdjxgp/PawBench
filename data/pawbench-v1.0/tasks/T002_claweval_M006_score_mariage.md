---
id: M006_score_mariage
name: Sheet Music Reproduction - Mariage d'Amour
category: multimodal
grading_type: hybrid
timeout_seconds: 1200
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T002_claweval_M006_score_mariage/fixtures/mariage1.png
  dest: fixtures/mariage1.png
labels:
  capabilities:
  - Code_Manipulation
  - Tool_Use
  modality:
    type: multimodal
    channels:
    - image
  scenario: Content_Creation/Design
  complexity: L3
  environment: closed
---
## Prompt

The workspace contains a sheet music image of **Mariage d'Amour** by Paul de Senneville:
- `fixtures/mariage1.png`

Please first view the image, then generate `output/output.html` reproducing the score using **inline SVG**:

1. Include the title (`Mariage d'Amour`) and composer (`Paul de Senneville`)
2. Draw two staves (treble + bass) with a brace
3. Display key signature: **g minor** (2 flats — Bb, Eb)
4. Reproduce **3 complete measures** with the right time signatures:
   - **M1 (4/4)**: treble has whole rest; bass plays 8 eighth notes in pairs (G2,D3 / G3,Bb3 / D3,G3 / Bb3,D3) — a g-minor arpeggio rising then falling
   - **M2 (4/4)**: identical to M1 (treble rest + same bass arpeggio)
   - **M3 (5/4 — time signature changes!)**: bass plays 5 pairs (10 eighth notes); treble enters with a dense ascending sixteenth-note run:
     - Beat 1: eighth rest + D5, Eb5
     - Beat 2: F5, G5, A5, Bb5 (ascending)
     - Beat 3: C6, D6, C6, Bb5 (peak then descend)
     - Beat 4: A5, G5, A5, Bb5 (oscillating)
     - Beat 5: D5 (quarter — lands)
5. Visual contrast must be clear: **M1–M2 sparse** (bass only), **M3 very dense** (many beamed sixteenth notes in treble)
6. Show the time-signature change from 4/4 to 5/4 between M2 and M3

Save the result to `output/output.html`.

## Expected Behavior

- Read `fixtures/mariage1.png`
- Produce a single self-contained HTML file with inline SVG
- Layout shows the dramatic contrast (empty treble in M1–M2, dense beamed run in M3)
- Save to `output/output.html`

## Grading Criteria

- [ ] Reads reference PNG (file_read)
- [ ] Output HTML exists with inline SVG (output_file_exists, has_svg)
- [ ] Title and composer present (metadata_present)
- [ ] Key signature (2 flats) and clefs (clefs_key)
- [ ] Time-signature change 4/4 → 5/4 indicated (time_change)
- [ ] M1–M2 bass arpeggio note labels (bass_arpeggio)
- [ ] M3 dense ascending run note labels (ascending_run)
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
        "metadata_present": 0.0,
        "clefs_key": 0.0,
        "time_change": 0.0,
        "bass_arpeggio": 0.0,
        "ascending_run": 0.0,
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

    if re.search(r"mariage1\.png|read_image|view_image|fixtures/mariage", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    if re.search(r"<svg\b", file_content, re.IGNORECASE):
        result["has_svg"] = 1.0

    has_title = bool(re.search(r"Mariage\s*d", file_content, re.IGNORECASE))
    has_composer = bool(re.search(r"Senneville", file_content, re.IGNORECASE))
    if has_title and has_composer:
        result["metadata_present"] = 1.0
    elif has_title or has_composer:
        result["metadata_present"] = 0.5

    has_treble = bool(re.search(r"treble|G\s*clef|𝄞", file_content, re.IGNORECASE))
    has_bass = bool(re.search(r"bass|F\s*clef|𝄢", file_content, re.IGNORECASE))
    has_flats = bool(re.search(r"2\s*flats|Bb|Eb|♭|flat", file_content, re.IGNORECASE))
    score = sum([has_treble, has_bass, has_flats]) / 3
    result["clefs_key"] = score

    has_44 = bool(re.search(r"4/4|\bC\b", file_content))
    has_54 = bool(re.search(r"5/4", file_content))
    if has_44 and has_54:
        result["time_change"] = 1.0
    elif has_54 or has_44:
        result["time_change"] = 0.5

    bass_pitches = set(re.findall(r"\b[A-G][#b]?[2-3]\b", file_content))
    target = {"G2", "D3", "G3", "Bb3"}
    overlap = bass_pitches & target
    if len(overlap) >= 3:
        result["bass_arpeggio"] = 1.0
    elif len(overlap) >= 2:
        result["bass_arpeggio"] = 0.5

    melody_pitches = set(re.findall(r"\b[A-G][#b]?[5-6]\b", file_content))
    melody_target = {"D5", "Eb5", "F5", "G5", "A5", "Bb5", "C6", "D6"}
    overlap_m = melody_pitches & melody_target
    if len(overlap_m) >= 5:
        result["ascending_run"] = 1.0
    elif len(overlap_m) >= 3:
        result["ascending_run"] = 0.5
    elif len(overlap_m) >= 1:
        result["ascending_run"] = 0.2

    return result
```

## LLM Judge Rubric

### Criterion 1: Note Accuracy & Time Change (Weight: 55%)

**Reference content:**
- Title: `Mariage d'Amour`, Composer: `Paul de Senneville`
- Key: g minor (2 flats: Bb, Eb)
- Time: starts 4/4, **changes to 5/4 in M3**, back to C in M4
- 3 complete measures shown
- Two staves: treble (top) + bass (bottom)

**M1 (4/4):**
- Treble: whole rest (completely empty)
- Bass: 8 eighth notes in pairs (g-minor arpeggio): G2,D3 / G3,Bb3 / D3,G3 / Bb3,D3 — rises from low G2 up to Bb3 then falls

**M2 (4/4):**
- Treble: whole rest (still empty)
- Bass: identical to M1

**M3 (5/4 — dramatic entry):**
- Time signature changes to 5/4 (5 beats)
- Bass: 5 pairs (10 eighth notes): G2,D3 / G3,Bb3 / D3,G3 / Bb3,D3 / G2,D3
- Treble enters with a fast ascending sixteenth-note run:
  - Beat 1: eighth rest + D5, Eb5 (two sixteenths)
  - Beat 2: F5, G5, A5, Bb5 (four sixteenths — ascending scale)
  - Beat 3: C6, D6, C6, Bb5 (four sixteenths — peak then descend)
  - Beat 4: A5, G5, A5, Bb5 (four sixteenths — oscillating)
  - Beat 5: D5 (quarter)

**KEY FEATURES to verify:**
1. M1–M2: treble must be empty (rests), bass has arpeggiated eighth-note pairs
2. M3: time signature changes to 5/4. Right hand suddenly fills with dense beamed sixteenth notes
3. The sixteenth-note run in M3 goes UP (D5→Eb5→F5→G5→A5→Bb5→C6→D6) then back DOWN
4. Visual contrast: M1–M2 sparse (bass only), M3 very dense (many beamed notes in treble)

**Scoring bands:**
- **0.0–0.2**: M3 has no dense ascending run, OR M1–M2 not sparse
- **0.2–0.4**: Ascending run exists but note positions mostly wrong
- **0.4–0.7**: General structure (sparse→dense) correct but details off
- **0.7–1.0**: Ascending scale run in M3 and sparse M1–M2 bass closely match

### Criterion 2: Clefs, Key Signature, Barlines (Weight: 25%)

- Correct key signature (2 flats: Bb, Eb)
- Treble clef + bass clef present
- Barlines between measures
- Time signature labels visible (C / 4/4 then 5/4)

**Scoring bands:**
- **1.0**: All notation elements correctly present
- **0.5–0.8**: Most present, minor issues
- **0.0–0.4**: Significant elements missing

### Criterion 3: Title, Composer, Overall Visual (Weight: 20%)

- Title and composer text visible
- Two-stave layout with brace
- Overall visual resemblance to reference

**Scoring bands:**
- **1.0**: Closely matches reference layout, all metadata present
- **0.5–0.8**: Recognizable, with minor differences
- **0.0–0.4**: Bare or mismatched
