---
id: M007_score_symphony
name: Sheet Music Reproduction - Symphony No. 5
category: multimodal
grading_type: hybrid
timeout_seconds: 1200
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T003_claweval_M007_score_symphony/fixtures/symphony1.png
  dest: fixtures/symphony1.png
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

The workspace contains a sheet music image of **Symphony No. 5 Mvt. 1** by Beethoven:
- `fixtures/symphony1.png`

Please first view the image, then generate `output/output.html` reproducing the score using **inline SVG**:

1. Include the title (`Symphony No. 5 Mvt. 1`), composer (`Beethoven`), tempo (`quarter = 170`)
2. Draw two staves (treble + bass) with a brace
3. Display key signature: **C minor** (3 flats — Bb, Eb, Ab); time signature: **2/4**
4. Reproduce **5 measures** containing the famous "Fate" motif (short-short-short-LONG):
   - **M1 (2/4)**: eighth rest + 3 beamed eighth notes on G4 (treble) and G2+G3 octave (bass)
   - **M2 (2/4)**: half note Eb4 (treble) + half note Eb2+Eb3 octave (bass)
   - **M3 (2/4)**: eighth rest + 3 beamed eighth notes on F4 (treble) and F2+F3 octave (bass) — same pattern as M1, but LOWER
   - **M4 (2/4)**: half note D4 with tie to M5 (treble) + half note D2+D3 octave with tie (bass)
   - **M5 (2/4)**: half note D4 continuation (treble); bass clef change to treble at end
5. Visual must show:
   - The "da-da-da-DUM" rhythm: rest + 3 beamed eighth notes, then a held half note
   - Pattern repeats: M1+M2 then M3+M4
   - M1 notes (G4) are higher than M3 notes (F4) — motif steps DOWN
   - Both staves mirror the same rhythmic pattern (octave doubles in bass)
   - Ties between M4 and M5

Save the result to `output/output.html`.

## Expected Behavior

- Read `fixtures/symphony1.png`
- Build a single self-contained HTML file with inline SVG containing all 5 measures
- The "fate" motif visual rhythm should be unmistakable
- Save to `output/output.html`

## Grading Criteria

- [ ] Reads reference PNG (file_read)
- [ ] Output HTML exists with inline SVG (output_file_exists, has_svg)
- [ ] Title and composer present (metadata_present)
- [ ] Key (3 flats), time 2/4, clefs (clefs_key_time)
- [ ] Motif rhythm signaled in SVG (motif_rhythm)
- [ ] Pitches G4, F4, Eb4, D4 referenced (motif_pitches)
- [ ] Octave doubling in bass (G2/G3, F2/F3 etc.) (bass_octaves)
- [ ] Ties present for M4–M5 (ties_present)
- [ ] Substantial output (>4KB) (substantial_output)

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
        "clefs_key_time": 0.0,
        "motif_rhythm": 0.0,
        "motif_pitches": 0.0,
        "bass_octaves": 0.0,
        "ties_present": 0.0,
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

    if re.search(r"symphony1\.png|read_image|view_image|fixtures/symphony", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    if re.search(r"<svg\b", file_content, re.IGNORECASE):
        result["has_svg"] = 1.0

    has_title = bool(re.search(r"Symphony.{0,10}5|Symphony.{0,10}No", file_content, re.IGNORECASE))
    has_composer = bool(re.search(r"Beethoven", file_content, re.IGNORECASE))
    if has_title and has_composer:
        result["metadata_present"] = 1.0
    elif has_title or has_composer:
        result["metadata_present"] = 0.5

    has_treble = bool(re.search(r"treble|G\s*clef|𝄞", file_content, re.IGNORECASE))
    has_bass = bool(re.search(r"bass|F\s*clef|𝄢", file_content, re.IGNORECASE))
    has_24 = bool(re.search(r"2/4", file_content))
    has_3flats = bool(re.search(r"3\s*flats|Bb|Eb|Ab|♭", file_content, re.IGNORECASE))
    score = sum([has_treble, has_bass, has_24, has_3flats]) / 4
    result["clefs_key_time"] = score

    rest_signals = bool(re.search(r"eighth.{0,5}rest|8th.{0,5}rest|rest.{0,40}eighth|eighth.?note|beam", file_content, re.IGNORECASE))
    half_signals = bool(re.search(r"half.{0,5}note|halfnote", file_content, re.IGNORECASE))
    motif_kw = bool(re.search(r"motif|fate|da-da-da", file_content, re.IGNORECASE))
    rhythm_count = sum([rest_signals, half_signals, motif_kw])
    if rhythm_count >= 2:
        result["motif_rhythm"] = 1.0
    elif rhythm_count == 1:
        result["motif_rhythm"] = 0.5

    melody_pitches = set(re.findall(r"\b[A-G][#b]?[2-5]\b", file_content))
    target = {"G4", "F4", "Eb4", "D4"}
    overlap = melody_pitches & target
    if len(overlap) >= 3:
        result["motif_pitches"] = 1.0
    elif len(overlap) >= 2:
        result["motif_pitches"] = 0.6
    elif len(overlap) >= 1:
        result["motif_pitches"] = 0.3

    bass_target = {"G2", "G3", "F2", "F3", "Eb2", "Eb3", "D2", "D3"}
    bass_overlap = melody_pitches & bass_target
    if len(bass_overlap) >= 4:
        result["bass_octaves"] = 1.0
    elif len(bass_overlap) >= 2:
        result["bass_octaves"] = 0.5

    if re.search(r"\btie\b|tied|tie-?to|slur", file_content, re.IGNORECASE):
        result["ties_present"] = 1.0

    return result
```

## LLM Judge Rubric

### Criterion 1: "Fate" Motif Rhythm (Weight: 45%)

**Reference:**
- Title: `Symphony No. 5 Mvt. 1`, Composer: Beethoven, Tempo: quarter = 170
- Key: C minor (3 flats: Bb, Eb, Ab); Time: 2/4
- 5 measures, two staves (treble + bass), joined by brace

**The famous "fate" motif (short-short-short-LONG):**

- **M1**: eighth rest + 3 beamed eighth notes — treble all on G4, bass octave G2+G3
- **M2**: one half note — treble on Eb4, bass octave Eb2+Eb3 (held, fills measure)
- **M3**: eighth rest + 3 beamed eighth notes — treble all on F4, bass octave F2+F3 (same pattern as M1, LOWER pitch)
- **M4**: half note treble D4 (with tie to M5), bass octave D2+D3 (with tie)
- **M5**: half note D4 continuation (tie); clef change to treble at end of bass

**KEY FEATURES to verify:**
1. The "da-da-da-DUM" pattern: M1 = rest + 3 beamed eighth notes, M2 = one held note. Repeats: M3 = rest + 3 beamed, M4 = held
2. M1 notes (G4) are HIGHER than M3 notes (F4) — the motif steps DOWN
3. M2 held note (Eb4) is LOWER than M1 notes (G4) — big drop
4. Both staves play the SAME rhythmic pattern (rest+3 in M1,M3; held in M2,M4)
5. Left hand plays octave doubles throughout

**Scoring bands:**
- **0.0–0.2**: Da-da-da-DUM rhythm not recognizable
- **0.2–0.4**: Groups of 3 notes present, but held notes or pitch steps wrong
- **0.4–0.7**: Motif recognizable, pitches or ties inaccurate
- **0.7–1.0**: Short-short-short-LONG pattern with correct pitch descent

### Criterion 2: Notation Detail (Weight: 30%)

- Correct key signature (3 flats: Bb, Eb, Ab)
- Time signature 2/4 visible
- Treble + bass clefs
- Ties between M4 and M5
- Octave doubling visible in bass

**Scoring bands:**
- **1.0**: All present and correct
- **0.5–0.8**: Most present, minor issues
- **0.0–0.4**: Significant missing elements

### Criterion 3: Title, Composer, Layout (Weight: 25%)

- Title `Symphony No. 5 Mvt. 1` and composer `Beethoven` text
- Tempo marking (`quarter=170` or equivalent)
- Two-stave layout with brace
- Overall visual match to reference

**Scoring bands:**
- **1.0**: All metadata visible, layout matches
- **0.5–0.8**: Most metadata present
- **0.0–0.4**: Bare or unrecognizable
