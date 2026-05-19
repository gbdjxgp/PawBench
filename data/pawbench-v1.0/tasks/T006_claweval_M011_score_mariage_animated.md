---
id: M011_score_mariage_animated
name: Animated Sheet Music - Mariage d'Amour
category: multimodal
grading_type: hybrid
timeout_seconds: 1200
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T006_claweval_M011_score_mariage_animated/fixtures/mariage1.png
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

Please first view the image, then generate `output/output.html` — an **interactive playback page** with:

1. **Score** reproduced using inline SVG (3 measures, two staves, brace, key g minor / 2 flats):
   - **M1 (4/4)**: treble whole rest; bass arpeggio G2,D3 / G3,Bb3 / D3,G3 / Bb3,D3
   - **M2 (4/4)**: identical to M1 (treble rest + same bass)
   - **M3 (5/4)**: time signature change to 5/4; bass 5 pairs (10 eighth notes); treble enters with **dense beamed ascending sixteenth-note run**: D5→Eb5→F5→G5→A5→Bb5→C6→D6, then descending, ending D5 quarter
2. Visual contrast: M1–M2 sparse (bass only), M3 very dense (many beamed sixteenths in treble)
3. **Piano keyboard** drawn below the score
4. **Play button** that, when clicked:
   - Highlights notes sequentially left-to-right
   - Lights up corresponding piano keys
   - Plays sound via the **Web Audio API**
5. Title (`Mariage d'Amour`), composer (`Paul de Senneville`)

Save the result to `output/output.html`.

## Expected Behavior

- Read `fixtures/mariage1.png`
- Build a single self-contained HTML file with inline SVG, JS, CSS
- Save to `output/output.html`

## Grading Criteria

- [ ] Reads reference PNG (file_read)
- [ ] Output exists with inline SVG (output_file_exists, has_svg)
- [ ] Title/composer present (metadata_present)
- [ ] Piano keyboard present (piano_present)
- [ ] Play button present (play_button)
- [ ] Web Audio API used (web_audio)
- [ ] Animation logic referenced (animation_logic)
- [ ] Bass arpeggio note pitches (bass_arpeggio)
- [ ] Treble ascending run pitches (ascending_run)
- [ ] Time signature change 4/4 → 5/4 indicated (time_change)
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
        "bass_arpeggio": 0.0,
        "ascending_run": 0.0,
        "time_change": 0.0,
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

    if re.search(r"mariage1\.png|read_image|view_image|fixtures/mariage", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    if re.search(r"<svg\b", file_content, re.IGNORECASE):
        result["has_svg"] = 1.0

    has_title = bool(re.search(r"Mariage", file_content, re.IGNORECASE))
    has_composer = bool(re.search(r"Senneville", file_content, re.IGNORECASE))
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

    bass_pitches = set(re.findall(r"\b[A-G][#b]?[2-3]\b", file_content))
    bass_target = {"G2", "D3", "G3", "Bb3"}
    overlap = bass_pitches & bass_target
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

    has_44 = bool(re.search(r"4/4|\bC\b", file_content))
    has_54 = bool(re.search(r"5/4", file_content))
    if has_44 and has_54:
        result["time_change"] = 1.0
    elif has_54 or has_44:
        result["time_change"] = 0.5

    return result
```

## LLM Judge Rubric

### Criterion 1: Score Visual Quality (Weight: 75%)

**Reference content:**
- Title: `Mariage d'Amour`, Composer: `Paul de Senneville`
- Key: g minor (2 flats: Bb, Eb), Time: 4/4 → 5/4 → 4/4. 3 measures.
- M1–2 (4/4): treble whole rests; bass eighth-note arpeggio pairs G2,D3 / G3,Bb3 / D3,G3 / Bb3,D3
- M3 (5/4): DRAMATIC ENTRY — treble enters with dense beamed sixteenth notes:
  - Ascending run D5→Eb5→F5→G5→A5→Bb5→C6→D6, then descending, ending on D5 quarter
  - This dense passage is the MOST distinctive visual element

**Visual contrast**: M1–2 sparse (bass only) → M3 very dense (many beamed sixteenths in treble)

**Scoring sub-items:**
- M1–M2 treble rests + bass arpeggio? (0.15)
- M3 shows dense ascending sixteenth-note run in treble (many beamed notes going UP)? (0.20)
- Clear visual contrast between sparse M1–2 and dense M3? (0.15)
- Piano keyboard present below score? (0.10)
- Play button and note highlight visible? (0.10)
- Correct key (2 flats), time signature change, clefs? (0.10)
- Layout clean and professional? (0.10)
- Title, composer? (0.10)

**Scoring bands:**
- **0.0–0.2**: M3 does not show a dense ascending run, OR M1–M2 are not sparse
- **0.2–0.5**: Some structure visible, many errors
- **0.5–0.8**: General sparse → dense contrast right, details off
- **0.8–1.0**: Dense ascending scale run in M3 + sparse M1–M2 closely match

### Criterion 2: Playback Animation (Weight: 25%)

Review the JavaScript:

- Different notes highlighted in different time steps? (0.30)
- Piano keys light up corresponding to played notes? (0.25)
- Highlight moves left-to-right through the score? (0.20)
- Progression speed appears reasonable? (0.15)
- Visual change between consecutive frames is clear (uses setTimeout/setInterval/requestAnimationFrame)? (0.10)

**Scoring bands:**
- **1.0**: Complete playback logic
- **0.6–0.8**: Most logic present
- **0.3–0.5**: Partial
- **0.0–0.2**: No animation logic detected
