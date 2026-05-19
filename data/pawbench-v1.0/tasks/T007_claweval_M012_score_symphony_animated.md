---
id: M012_score_symphony_animated
name: Animated Sheet Music - Symphony No. 5
category: multimodal
grading_type: hybrid
timeout_seconds: 1200
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T007_claweval_M012_score_symphony_animated/fixtures/symphony1.png
  dest: fixtures/symphony1.png
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

The workspace contains a sheet music image of **Symphony No. 5 Mvt. 1** by Beethoven:
- `fixtures/symphony1.png`

Please first view the image, then generate `output/output.html` — an **interactive playback page** with:

1. **Score** reproduced using inline SVG (5 measures, two staves, brace, key C minor / 3 flats, time 2/4):
   - **M1**: eighth rest + 3 beamed eighth notes on G4 (treble) and G2+G3 octave (bass)
   - **M2**: half note Eb4 (treble) + Eb2+Eb3 octave (bass) — held, fills measure
   - **M3**: eighth rest + 3 beamed eighth notes on F4 (treble) and F2+F3 octave (bass) — same pattern as M1, LOWER
   - **M4**: half note D4 with tie to M5 (treble) + D2+D3 with tie (bass)
   - **M5**: half note D4 continuation
2. The **da-da-da-DUM** motif must be visually unmistakable
3. **Piano keyboard** drawn below the score
4. **Play button** that, when clicked:
   - Highlights notes sequentially left-to-right
   - Lights up corresponding piano keys
   - Plays sound via the **Web Audio API**
5. Title (`Symphony No. 5 Mvt. 1`), composer (`Beethoven`), tempo (`quarter = 170`)

Save the result to `output/output.html`.

## Expected Behavior

- Read `fixtures/symphony1.png`
- Build a single self-contained HTML file
- Save to `output/output.html`

## Grading Criteria

- [ ] Reads reference PNG (file_read)
- [ ] Output exists with inline SVG (output_file_exists, has_svg)
- [ ] Title/composer present (metadata_present)
- [ ] Piano keyboard SVG present (piano_present)
- [ ] Play button (play_button)
- [ ] Web Audio API used (web_audio)
- [ ] Animation logic referenced (animation_logic)
- [ ] Motif pitches G4, F4, Eb4, D4 (motif_pitches)
- [ ] Bass octave doubles G2/G3, F2/F3 etc. (bass_octaves)
- [ ] Ties present M4–M5 (ties_present)
- [ ] Substantial output (>6KB) (substantial_output)

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
        "piano_present": 0.0,
        "play_button": 0.0,
        "web_audio": 0.0,
        "animation_logic": 0.0,
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
            if len(file_content) > 6000:
                result["substantial_output"] = 1.0
            elif len(file_content) > 2500:
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

    if re.search(r"piano|keyboard|key.{0,4}white|key.{0,4}black", file_content, re.IGNORECASE):
        result["piano_present"] = 1.0

    if re.search(r"<button|class\s*=\s*[\"']play|id\s*=\s*[\"']play|>\s*Play\s*<", file_content, re.IGNORECASE):
        result["play_button"] = 1.0

    if re.search(r"AudioContext|webkitAudioContext|OscillatorNode|createOscillator|Web\s*Audio", file_content, re.IGNORECASE):
        result["web_audio"] = 1.0

    if re.search(r"setInterval|setTimeout|requestAnimationFrame|highlight|animate|@keyframes", file_content, re.IGNORECASE):
        result["animation_logic"] = 1.0

    pitches = set(re.findall(r"\b[A-G][#b]?[2-5]\b", file_content))
    target = {"G4", "F4", "Eb4", "D4"}
    overlap = pitches & target
    if len(overlap) >= 3:
        result["motif_pitches"] = 1.0
    elif len(overlap) >= 2:
        result["motif_pitches"] = 0.6

    bass_target = {"G2", "G3", "F2", "F3", "Eb2", "Eb3", "D2", "D3"}
    bass_overlap = pitches & bass_target
    if len(bass_overlap) >= 4:
        result["bass_octaves"] = 1.0
    elif len(bass_overlap) >= 2:
        result["bass_octaves"] = 0.5

    if re.search(r"\btie\b|tied|tie-?to|slur", file_content, re.IGNORECASE):
        result["ties_present"] = 1.0

    return result
```

## LLM Judge Rubric

### Criterion 1: Score Visual Quality (Weight: 75%)

**Reference content:**
- Title: `Symphony No. 5 Mvt. 1`, Composer: Beethoven, Tempo: 170
- Key: C minor (3 flats), Time: 2/4, 5 measures
- The famous "da-da-da-DUM" motif:
  - M1: rest + 3 beamed eighth notes on G4 (both staves). Left hand: octave G2+G3
  - M2: one half note on Eb4 (HELD, big drop from G). Left: Eb2+Eb3
  - M3: rest + 3 beamed eighth notes on F4 (LOWER than M1). Left: F2+F3
  - M4: one half note on D4, tied to M5. Left: D2+D3
- Pattern: rest+3notes, HOLD, rest+3notes, HOLD — the motif steps DOWN (G→Eb, F→D)
- Both staves mirror the same rhythm

**Scoring sub-items:**
- Is rest + 3 beamed notes pattern visible in M1 and M3? (0.20)
- Are M2 and M4 held half notes (short-short-short-LONG rhythm)? (0.15)
- Do M1 notes sit higher than M3 (G vs F, stepping down)? (0.10)
- Both staves mirror same pattern? (0.05)
- Piano keyboard present below score? (0.10)
- Play button and note highlight visible? (0.10)
- Correct key (3 flats), time (2/4), ties M4–M5? (0.10)
- Layout clean, title, composer? (0.10)
- Overall visual match to reference? (0.10)

**Scoring bands:**
- **0.0–0.2**: Da-da-da-DUM pattern not recognizable
- **0.2–0.5**: Some structure visible, many errors
- **0.5–0.8**: Motif recognizable, details off
- **0.8–1.0**: Short-short-short-LONG with correct pitch descent and held notes

### Criterion 2: Playback Animation (Weight: 25%)

Review the JavaScript:

- Different notes highlighted in different time steps? (0.30)
- Piano keys light up corresponding to played notes? (0.25)
- Highlight moves left-to-right through the score? (0.20)
- Progression speed appears reasonable? (0.15)
- Visual change between consecutive frames clear (uses setTimeout/setInterval/rAF)? (0.10)

**Scoring bands:**
- **1.0**: Complete playback logic
- **0.6–0.8**: Most present
- **0.3–0.5**: Partial
- **0.0–0.2**: No animation logic detected
